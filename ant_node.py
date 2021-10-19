#ANT ROUTING LIB
#TODO BETTER handle logging and levels
#TODO Drop invoice after timeout 10s ?
#TODO RETRY if payment failed/timeout

import asyncio 
import random
import time

from ant_utils import get_timestamp, seed_bar, lifespan
from data import *


from colorama import init
from termcolor import colored
 
init()
 

class Node:
    """ Represents a Lightning node
        with data for ant routing""" 

    def __init__(self, node_id, peers):
        # Node id and local topology
        self.node_id = node_id
        self.peers = peers
        self.messages = []
        self.delay = 0.1 + 1*random.random()/2 
        self.fee   = random.randint(10,30)
        self.maxfees = random.randint(250,300)
        self.balance = random.randint(50,300)*1000
        self.payment = None
        self.is_running = False

        # Additional logging data
        self.ant_data = AntData()
        self.paid_list = []
        self.total_messages = 0
        self.processed_messages = 0
        self.msgs = []
        self.seedmatches = {}
        self.created = 0


    def set_nodes(self, nodes):
        self.nodes = nodes


    def __repr__(self):
        return f'Node({self.node_id}, {set(self.peers)})'


    def _process_msg(self, msg):
        #print(f'{self.node_id:02d}: {msg.__class__.__name__} @ {msg}')
        self.processed_messages += 1
        
        delta = lifespan(msg)
        if delta > 80:  
            print(colored(f"stale message received in {delta/10:.2f}s", "yellow", "on_red"))
            #return

        process_switch = {
            'PheroMsg': self.process_phero,
            'MatchMsg': self.process_match,
            'ConfMsg' : self.process_conf,
            'CheckMsg': self.process_check,
                }
        
        msg_type = msg.__class__.__name__

        if msg_type not in process_switch:
            print("Error in msg type")

        process_switch[msg_type](msg)


    def is_busy(self):
        return self.payment


    def pay(self, amount, node_to):
        node_bob = self.nodes[node_to]

        if self.is_busy() or node_bob.is_busy():
            #print("Error: previous payment pending!")
            return False

        seed = f'{random.randint(0,2**32-1):08x}'
        c_0 = random.randint(64,128)

        payment_bob = Payment(
            seed,
            amount,
            None,
            True,
            False,
            node_to,
            self.node_id,
            node_bob.maxfees + self.maxfees,
            c_0, [], None)
    
        payment_alice = Payment(
            seed,
            amount,
            None,
            False,
            True,
            node_to,
            self.node_id,
            node_bob.maxfees + self.maxfees,
            c_0, [], None)        

        self.set_payment(payment_alice)
        node_bob.set_payment(payment_bob)    

        #print(f'Alice{self.node_id:02d} pays {amount:04d} to Bob{node_to:02d} with seed={seed}')
        return True


    def set_payment(self, payment):
        self.payment = payment
        bit = "0" if self.payment.alice else "1"
        timestamp = get_timestamp()
        self.payment.timestamp = timestamp

        msg = PheroMsg(
            bit + self.payment.seed,
            self.payment.c_0 - 1, #so that they send c_0 to neighbors
            self.node_id,
            self.payment.fees_max // 2,
            self.payment.amount,
            timestamp)

        self.add_msg(msg)


    def add_msg(self, msg):
        #TODO? Need to check from ?
    
        self.msgs.append(msg)

        peers = [self.node_id, *self.peers]
        if self.payment and self.payment.alice:
            peers.append(self.payment.node_bob)

        if msg.from_id not in peers:
            print(colored(f"ERROR: Node{self.node_id:02d} received from unknown peer", "blue", "on_yellow"))
            print(f"from={msg.from_id} peers={self.peers}")
            print(msg)

        self.total_messages += 1
        self.messages.append(msg)

    def create_and_send_match(self, msg):
        #print(f"{self.node_id} creates match")
        self.created += 1
        pheromone = msg.pheromone
        seed = pheromone[1:]
        _,seed_data = self.ant_data.get_pheromone(pheromone)
        fees0 = seed_data.fees0
        fees1 = seed_data.fees1
        c0 = seed_data.counter0
        c1 = seed_data.counter1
        
        F = fees0 + fees1 - self.fee 
        C = c0 + c1 + 1 

        if F < 0: 
            print("Matched Fees too low")
            return

        # Check if not present ?
        match_id = random.randint(0, 2**32-1)
        if seed_data.sender1 is None:
            print("Sender1 is none")
            exit()

        self.ant_data.add_match(match_id, seed_data.sender1)
        if seed_data.sender1 not in [self.node_id, *self.peers]: 
            print(f"Node{self.node_id} SENDER{seed_data.sender1} NOT IN PEERS")
            return

        # Send the Match Messages
        m0 = "00" + seed
        m1 = "01" + seed
        t = msg.timestamp
        match_1 = MatchMsg(m1, match_id, self.node_id, c1, C, F, t)
        match_0 = MatchMsg(m0, match_id, self.node_id, c0, C, F, t)
        self.nodes[seed_data.sender0].add_msg(match_0)
        self.nodes[seed_data.sender1].add_msg(match_1)

        if seed in self.seedmatches:
            self.seedmatches[seed].append(match_id)
        else: 
            self.seedmatches[seed] = [match_id]

#        print(f"matched at Node{self.node_id} with counter={msg.counter} id={match_id}")

                    
    def handle_confirmation(self, match): 
        #print(f"Handling confirmation {match}")
        # Only Alice
        if match != self.payment.match:
            print(colored("handle_conf error", "red", "on_green"))
            print(match.match_id, self.payment.match.match_id)
            return

        size = random.randint(10,20)
        check_list = list(set([ random.randint(0,256) for _ in range(size)]))
        self.payment.check_list = check_list

        conf_msg = ConfMsg(match.match_id, self.node_id, check_list, match.timestamp)
    
        node_to = self.nodes[match.from_id]
        node_to.add_msg(conf_msg)        

                    
    def handle_check(self, msg):
        # Only Alice
        len_checks = len(msg.check_list) - len(self.payment.check_list) 
        match = self.ant_data.get_special_match(msg.match_id)
        if match is None:
            print("HANDLE CHECK ERROR",)
            print(f"{lifespan(msg)/10:.2f}s")
            print(msg.match_id, "not found")
            print(self.payment)
            return

        sum_C = match.sum_counter

        c_0 = self.payment.c_0
        if sum_C - 2*c_0 - len_checks != 0:
            print(colored("cheater detected TODO", "green", "on_red"))
            print(f"C = {sum_C}, 2*c_0 = {2*c_0}, len(mcl)={len(msg.check_list)}, len(pcl)={len(self.payment.check_list)}")
            print(f' C -2c_0 = {sum_C - 2*c_0} != {len_checks} = len_checks')
            print(f"lifespan = {lifespan(msg)/10:.2f}s")
            print("## CHECK ##")
            print(self.payment)
            print(msg)
            print(self.ant_data.special_match)

            #TODO remove match and choose another one
            return

        size = random.randint(10,20)
        check_list = list(set([ random.randint(0,256) for _ in range(size)]))
        new_check_list = msg.check_list[-len_checks:] + check_list

        check_msg = CheckMsg(msg.match_id,
                             self.node_id,
                             new_check_list,
                             msg.timestamp)

        to_id = self.ant_data.get_special_match(msg.match_id).from_id
        node_to = self.nodes[to_id]
        node_to.add_msg(check_msg)        
        

    def process_phero(self, msg):
        #print(f'{self.node_id:02d} got pheromone {msg.pheromone}')
        fees_remaining = msg.fees_remaining - self.fee
        if fees_remaining < 0: return

        p0 = msg.pheromone[0] == '0'
        p1 = not p0

        found, prev_data = self.ant_data.get_pheromone(msg.pheromone)
        if not found:
            if not prev_data:
                new_data = SeedData(
                        msg.amount,
                        msg.fees_remaining if p0 else None,
                        msg.fees_remaining if p1 else None,
                        msg.counter if p0 else None,
                        msg.counter if p1 else None,
                        msg.from_id if p0 else None,
                        msg.from_id if p1 else None,
                        p0, p1)

                self.ant_data.add_pheromone(msg.pheromone, new_data)
            else: #Update Seed data 
                if p0:
                    prev_data.counter0 = msg.counter
                    prev_data.sender0 = msg.from_id
                    prev_data.fees0 = msg.fees_remaining
                    prev_data.pheromone0 = True
                else:
                    prev_data.counter1 = msg.counter
                    prev_data.sender1 = msg.from_id
                    prev_data.fees1 = msg.fees_remaining
                    prev_data.pheromone1 = True
             
        else: #Pheromone is found
            # Ignore if counter higher than previous data
            if (p0 and prev_data.counter0 <= msg.counter or
                p1 and prev_data.counter1 <= msg.counter):
                return

            # otherwise, update with received data
            if p0:
                prev_data.counter0 = msg.counter
                prev_data.sender0 = msg.from_id
                prev_data.fees0 = msg.fees_remaining
                prev_data.pheromone0 = True
            else:
                prev_data.counter1 = msg.counter
                prev_data.sender1 = msg.from_id
                prev_data.fees1 = msg.fees_remaining
                prev_data.pheromone1 = True
            
        pb_found = prev_data and prev_data.pheromone0 and prev_data.pheromone1

        if not pb_found: #dual pheromone not received yet
            for node_id in self.peers:
                node = self.nodes[node_id]
                # TODO: use balance in _payment channel_ 
                if (node.balance >= msg.amount and 
                    node.node_id != msg.from_id):

                    new_data = PheroMsg(
                        msg.pheromone,
                        msg.counter + 1,
                        self.node_id,
                        fees_remaining,
                        msg.amount,
                        msg.timestamp)

                    node.add_msg(new_data)                    
        else: #pheromone and its dual found
            self.create_and_send_match(msg)


    def process_match(self, msg):
        #print(f"{self.node_id:02d} got match {msg}")
        p = msg.pheromone[1:]
        (found, p_data) = self.ant_data.get_pheromone(p)

        if not p_data:
            print(f"{self.node_id} Match{msg.match_id} dropped, too late ({lifespan(msg)/10:02f}s)")
            print(p)
            print(sorted({k:v for trees in self.ant_data.phero for k,v in trees.items()}))
            return

        if p[0] == "0":
            if found: #TODO must be true 
                if p_data.counter0 != msg.counter - 1:
                    return

                # Checks if we are Alice
                if (self.payment and 
                    self.payment.seed == msg.pheromone[2:] and 
                    self.payment.alice): 

                    match = MatchData(msg.match_id,
                                  msg.from_id,
                                  msg.sum_counter,
                                  msg.fees,
                                  msg.timestamp) 

                    m_data = self.ant_data.get_special_match(msg.match_id)
                    if m_data is not None:
                        print(colored(f"Node{self.node_id} match {msg.match_id} already there", "red", "on_yellow"))
                        print([m for m in self.msgs if msg.__class__.__name__ == "MatchMsg" and m.match_id == msg.match_id])
                        print(m_data)
                        print(msg)
                        exit()

                    self.ant_data.add_special_match(msg.match_id, match)

                else: # Not Alice
                    m_data = self.ant_data.get_match(msg.match_id)
                    if m_data is not None:
                        print(colored(f"Node{self.node_id} match {msg.match_id} already there", "red", "on_yellow"))
                        print([m for m in self.msgs if m.__class__.__name__ == "MatchMsg" and m.match_id == msg.match_id])
                        print(m_data)
                        print(msg)
                        exit()

                    self.ant_data.add_match(msg.match_id, msg.from_id)

                    match_msg = MatchMsg(msg.pheromone,
                                msg.match_id,
                                self.node_id,
                                msg.counter - 1,
                                msg.sum_counter,
                                msg.fees,
                                msg.timestamp)

                    self.nodes[p_data.sender0].add_msg(match_msg)
            #else:
            #    print(colored("NOT FOUND", "red", "on_black"))
                    
        else: # p[0] == "1":
            if p_data.pheromone1:
                if p_data.counter1 != msg.counter - 1:
                    return

                self.ant_data.add_match(msg.match_id, p_data.sender1)

                # TODO added: if Bob,then notify match is ready?
                if (self.payment and self.payment.seed == msg.pheromone[2:] and
                    self.payment.bob):
                    node_alice = self.nodes[self.payment.node_alice]
                    node_alice.payment.ready.append(msg.match_id)


                # Check if we aren't involved in current payment
                if not self.payment or self.payment.seed != msg.pheromone[2:]:
                    match_msg = MatchMsg(msg.pheromone,
                                    msg.match_id,
                                    self.node_id,
                                    msg.counter - 1,
                                    msg.sum_counter,
                                    msg.fees,
                                    msg.timestamp)

                    self.nodes[p_data.sender1].add_msg(match_msg)

            else: 
                print(colored(" #### pheromone not found!", "red", "on_green"))
                print(p_data)
                print(msg.pheromone)
                print(f"{lifespan(msg)/10:.1f}s")
                return




    def process_conf(self, msg):
        # print(f"node {self.node_id:02d} got conf for match {msg.match_id}")
        # Check if involved in current payment
        if (self.payment and 
            self.payment.match and 
            self.payment.match.match_id == msg.match_id):
            # Bobs sends back the confirmation data to Alice
            if self.payment.bob:
                node_alice = self.nodes[self.payment.node_alice]
                new_msg = ConfMsg(msg.match_id,
                                  self.node_id,
                                  msg.check_list,
                                  msg.timestamp)
                node_alice.add_msg(new_msg)
                return
        
            # Alice kickstarts the check phase
            if self.payment.alice:
                check_msg = ConfMsg(msg.match_id, 
                                 self.node_id, 
                                 msg.check_list, 
                                 msg.timestamp)

                self.handle_check(check_msg)
                return

        match = self.ant_data.get_match(msg.match_id)
        if match is not None:
            check = random.randint(0, 256)
            new_check_list = list(msg.check_list)
            new_check_list.append(check)

            self.ant_data.add_confirmation(msg.match_id, 
                ConfData(msg.match_id, match, check, msg.timestamp))

            conf_msg = ConfMsg(msg.match_id,
                               self.node_id,
                               new_check_list,
                               msg.timestamp)
            
            
            node_to = self.nodes[match]
            node_to.add_msg(conf_msg)
        else:
            print(colored("conf error", "red", "on_white"))
            print(f"node{self.node_id:02d} Conf error at {lifespan(msg)/10:.2f}s for {msg.match_id}")
            print(self.payment)
            print(self.ant_data.match)
            print(self.ant_data.get_special_match(msg.match_id))
            print([m for m in self.messages])
            exit()
            
    

    def process_check(self, msg):
        #print(f"{self.node_id} got check")

        #TODO payment match helper?
        if (self.payment and 
            self.payment.match and
            self.payment.match.match_id == msg.match_id):

            if self.payment.alice:        
                self.route_payment(msg)
                return

            if self.payment.bob:
                node_alice = self.nodes[self.payment.node_alice]
                check_msg = CheckMsg(msg.match_id,
                               self.node_id,
                               msg.check_list,
                               msg.timestamp)
         
                node_alice.add_msg(check_msg)
                return

        c_data = self.ant_data.get_confirmation(msg.match_id)
        if c_data is not None:
            if msg.check_list[0] == c_data.check_num:
                conf_msg = CheckMsg(msg.match_id,
                                   self.node_id, # useless ?
                                   msg.check_list[1:],
                                   msg.timestamp)
                node_to = self.nodes[c_data.from_id]
                node_to.add_msg(conf_msg)

            else:
                print("cheater detected?")
        
    def _fetch_route(self, match, payment=None):
        #Only Alice
        node = match.from_id
        route = [self.node_id]
        while node not in route and node is not None:
            route.append(node)
            from_id = self.nodes[node].ant_data.get_match(match.match_id)
            
            if from_id is None:
                #print(f"from_id None for Node {node} at match_id = {match.match_id}")
                #print(match)
                #if payment: print(payment)
                pass
            node = from_id

        return route

    def choose_match(self):
        #print(f"{self.node_id:02d} Choosing a match")
        if self.payment.match is not None:
            print("MATCH ALREADY CHOSEN!")
        matches = {k:v for m in self.ant_data.special_match
                   for k,v in m.items()}
        if len(matches) == 0:
            #print("No matched seed found")
            return

        
        #print(len(matches))
        #for match_id, match in matches.items():
        #    print(match_id, self._fetch_route(match))

        mini = max(match.fees for match in matches.values())
        mini_id = [match.match_id for match 
                     in matches.values() 
                     if match.fees == mini][0]

        if mini_id not in self.payment.ready:
            #print(colored(f"match {mini_id} not ready", "red", "on_yellow"))
            #print(self.payment.ready)
            return None

        match = self.ant_data.get_special_match(mini_id)

        return match

    async def ant_route(self):
        while self.is_running:
            #  print(self.node_id, len(self.messages))
            if len(self.messages) != 0:
                if len(self.messages) > 900:
                    print(f"node{self.node_id} has {len(self.messages)} pending msgs")
                for _ in range(min(100, len(self.messages))):
                    msg = self.messages.pop(0)
                    self._process_msg(msg)

           # Check and select matched seeds
            if (self.payment and self.payment.alice):

                delta_t = lifespan(self.payment)
                # Choose match after a bit         
                if (delta_t >= 25 and not self.payment.match):
                    # TODO test all paths ?
                    match = self.choose_match() 

                    if match is not None:
                        self.payment.match = match
                        
                        route = self._fetch_route(match)
                        #print(f"Match_{match.match_id} for {self.payment.seed} route: {route}")
                        self.payment.route = route
                        node_bob = self.nodes[self.payment.node_bob]
                        node_bob.payment.match = match
                        node_bob.payment.route = route

                        self.handle_confirmation(match)

            await asyncio.sleep(self.delay)  

            #except Exception as e:
            #    print("Error: ", str(e))

    def route_payment(self, msg):
        #Only alice
        match = self.payment.match

        delta = lifespan(self.payment) 
        fees_paid = self.payment.fees_max - match.fees

        sum_C = match.sum_counter
        c_0 = self.payment.c_0
        num_hops = sum_C - 2*c_0  
         
        print(f"Alice{self.node_id:02d} paid {self.payment.amount} to Bob{self.payment.node_bob:02d} fees={fees_paid:03d} in {delta/10}s hops={num_hops+1} via {self.payment.route} seed={self.payment.seed} id={match.match_id}")
        #pf.payment)

        # Consider payment done
        self.ant_data.clear_special_match()

        self.payment.duration = delta
        self.paid_list.append(self.payment)

        self.nodes[self.payment.node_bob].payment = None
        self.payment = None
        


    def start(self):
        self.is_running = True

    def stop(self):
        self.is_running = False

