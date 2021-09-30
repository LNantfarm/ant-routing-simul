#ANT ROUTING LIB
#TODO Time-limit of seeds
#TODO handle multi seeds (currently, just one)
#TODO handle logging and levels

import asyncio 
import random
import time

from ant_utils import get_timestamp, seed_bar
from ant_data import PheroData, PheroMsg, MatchData, MatchMsg, ConfData, ConfMsg, CheckMsg, Payment


class Node:
    """ Represents a Lightning node
        with data for ant routing""" 

    def __init__(self, node_id, peers):
        # Node id and local topology
        self.node_id = node_id
        self.peers = peers
        self.messages = []
        self.delay = random.random()/10 + 0.01
        self.fee   = random.randint(10,30)
        self.maxfees = random.randint(250,300)
        self.balance = random.randint(50,300)*1000
 
        self.payment = None
        
        # Memory data
        self.phero_data = dict()
        self.match_data = dict()
        self.conf_data = dict()
        self.special_match_data = dict()

        self.is_running = False


    def __repr__(self):
        return f'Node({self.node_id}, {set(self.peers)})'


    def _process_msg(self, msg):
        #print(f'{self.node_id}: {msg.__class__.__name__} @ {msg}')
        
        delta = (get_timestamp() - msg.timestamp) % 256
        if delta > 60: #6 seconds  
            #print(f"msg dropped {msg}")
            #return
            pass

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


    def set_nodes(self, nodes):
        self.nodes = nodes


    def is_busy(self):
        return self.payment


    def insert_pheromone(self, msg):
        pass

    def insert_match(self, msg):
        pass

    def insert_confirmation(self, msg):
        pass
 
    def pay(self, amount, node_to):
        node_bob = self.nodes[node_to]

        if self.is_busy() or node_bob.is_busy():
            print(self.payment, node_bob.payment)
            print("Error: previous payment pending!")
            return

        seed = f'{random.randint(0,2**32-1):08x}'
        c_0 = random.randint(64,128)

        payment_bob = Payment(
            seed,
            amount,
            True,
            False,
            node_to,
            self.node_id,
            node_bob.maxfees + self.maxfees,
            c_0)
    
        payment_alice = Payment(
            seed,
            amount,
            False,
            True,
            node_to,
            self.node_id,
            node_bob.maxfees + self.maxfees,
            c_0)
        
        self.set_payment(payment_alice)
        node_bob.set_payment(payment_bob)    


    def set_payment(self, payment):
        #TODO must be private
        self.payment = payment
        bit = "0" if self.payment.alice else "1"
        msg = PheroMsg(
            bit + self.payment.seed,
            self.payment.c_0 - 1, #so that they send c_0 to neighbors
            self.node_id,
            self.payment.fees_max // 2,
            self.payment.amount,
            get_timestamp())

        self.add_msg(msg)


    def add_msg(self, msg):
        #TODO? Need to check from ?
        self.messages.append(msg)

    def create_and_send_match(self, phero):
        #print(f"matched at {self.node_id}")

        seed = phero[1:]
        p0_data = self.phero_data["0" + seed]
        p1_data = self.phero_data["1" + seed]
        fees0 = p0_data.fees_remaining
        fees1 = p1_data.fees_remaining
        c0 = p0_data.counter
        c1 = p1_data.counter
        
        F = fees0 + fees1 - self.fee 
        C = c0 + c1 + 1 

        if F < 0: 
            print("Matched Fees too high")
            return

        m0 = "00" + seed
        m1 = "01" + seed

        # Check if not present ?
        match_id = random.randint(0,256)

        self.match_data[match_id] = p1_data.from_id

        t = p0_data.timestamp

        match_0 = MatchMsg(m0, match_id, self.node_id, p0_data.counter, C, F, t)
        match_1 = MatchMsg(m1, match_id, self.node_id, p1_data.counter, C, F, t)

        #send the Match Messages
        self.nodes[p0_data.from_id].add_msg(match_0)
        self.nodes[p1_data.from_id].add_msg(match_1)

                    
    def handle_confirmation(self, match): 
        #print(f"Handling confirmation {match}")
        # Only Alice
        size = random.randint(10,20)
        check_list = list(set([ random.randint(0,256) for _ in range(size)]))
        self.payment.check_list = check_list

        conf_msg = ConfMsg(
                match.match_id,
                self.node_id,
                check_list,
                match.timestamp)
        
        node_to = self.nodes[match.from_id]
        node_to.add_msg(conf_msg)        

                    
    def handle_check(self, msg):
        # Only Alice
        len_checks = len(msg.check_list) - len(self.payment.check_list) 
        match =  self.special_match_data[msg.match_id]
        sum_C = match.sum_counter
        c_0 = self.payment.c_0
        if sum_C - 2*c_0 - len_checks != 0:
            print("cheater detected TODO", self.payment)
            print(f' C -2c_0 = {sum_C - 2*c_0} != {len_checks} = len_checks')
            #TODO remove match and choose another one
            return

        
        size = random.randint(10,20)
        check_list = list(set([ random.randint(0,256) for _ in range(size)]))
        new_check_list = msg.check_list[-len_checks:] + check_list

        check_msg = CheckMsg(msg.match_id,
                             self.node_id,
                             new_check_list,
                             msg.timestamp)

        node_to = self.nodes[self.special_match_data[msg.match_id].from_id]
        node_to.add_msg(check_msg)        
        

    def process_phero(self, msg):
        #print(f'{self.node_id} got seed {msg.seed}')
        fees_remaining = msg.fees_remaining - self.fee

        new_data = PheroData(
                        msg.seed,
                        msg.counter,
                        msg.from_id,
                        msg.fees_remaining,
                        msg.amount,
                        msg.timestamp)

        if fees_remaining < 0: 
            #print("fees too high")
            return
    
        if msg.seed not in self.phero_data:
            self.phero_data[msg.seed] = new_data
        else:
            prev_data = self.phero_data[msg.seed]
            if prev_data.counter <= msg.counter:
                return

            self.phero_data[msg.seed] = new_data
                    
        seed_b = seed_bar(msg.seed)          
        if seed_b not in self.phero_data:
            for node_id in self.peers:
                node = self.nodes[node_id]
                if (node.balance >= msg.amount and 
                    node.node_id != msg.from_id):

                    new_data = PheroMsg(
                        msg.seed,
                        msg.counter + 1,
                        self.node_id,
                        fees_remaining,
                        msg.amount,
                        msg.timestamp)

                    node.add_msg(new_data)                    
        else:
            self.create_and_send_match(msg.seed)


    def process_match(self, msg):
        #print(f"{self.node_id:02d} got match {msg}")
        if msg.seed[1] == "0":
            p0 = msg.seed[1:]
            if p0 in self.phero_data:
                p0_data = self.phero_data[p0]
                if p0_data.counter != msg.counter - 1:
                    return

                if (self.payment and 
                    self.payment.seed == msg.seed[2:] and 
                    self.payment.alice): 

                    match = MatchData(msg.match_id,
                                  msg.from_id,
                                  msg.sum_counter,
                                  msg.fees,
                                  msg.timestamp) 

                    #What if match already there ?
                    if msg.match_id in self.special_match_data:
                        #print("WARNING: overwriting match")
                        pass
                    self.special_match_data[msg.match_id] = match

                else:
                    self.match_data[msg.match_id] = msg.from_id

                    match_msg = MatchMsg(msg.seed,
                                msg.match_id,
                                self.node_id,
                                msg.counter - 1,
                                msg.sum_counter,
                                msg.fees,
                                msg.timestamp)

                    self.nodes[p0_data.from_id].add_msg(match_msg)
                    
        else: # msg.seed[1] == "1":
            p1 = msg.seed[1:]
            if p1 in self.phero_data:
                p1_data = self.phero_data[p1]
                if p1_data.counter != msg.counter - 1:
                    return

                self.match_data[msg.match_id] = p1_data.from_id

            if not self.payment or self.payment.seed != msg.seed[2:]:
                match_msg = MatchMsg(msg.seed,
                                msg.match_id,
                                self.node_id,
                                msg.counter - 1,
                                msg.sum_counter,
                                msg.fees,
                                msg.timestamp)

                self.nodes[p1_data.from_id].add_msg(match_msg)


    def process_conf(self, msg):
        #print(f"node {self.node_id:02d} got conf for match {msg.match_id}")
        # If bob or alice ?
        
        if (self.payment and 
            self.payment.match and 
            self.payment.match.match_id == msg.match_id):
            if self.payment.bob:
                node_alice = self.nodes[self.payment.node_alice]
                node_alice.add_msg(msg)
                return
        
            if self.payment.alice:
                check_msg = CheckMsg(msg.match_id, 
                                 msg.from_id, 
                                 msg.check_list, 
                                 msg.timestamp)

                self.handle_check(check_msg)
                return

        if msg.match_id in self.match_data:
            check = random.randint(0,256)
            new_check_list = list(msg.check_list)
            new_check_list.append(check)

            self.conf_data[msg.match_id] = ConfData(msg.match_id,
                self.match_data[msg.match_id],
                check,
                msg.timestamp)

            conf_msg = ConfMsg(msg.match_id,
                               msg.from_id,
                               new_check_list,
                               msg.timestamp)
            
            try:
                node_to = self.nodes[self.match_data[msg.match_id]]
                node_to.add_msg(conf_msg)
            except:
                print("matching error")
        else:
            print(f"""node {self.node_id:02d} Confirmation error
                    match: {msg.match_id},
                    {list(self.match_data.keys())}""")

    

    def process_check(self, msg):
        #print(f"{self.node_id} got check")

        #TODO payment match helper
        if (self.payment and 
            self.payment.match and
            self.payment.match.match_id == msg.match_id):

            if self.payment.alice:        
                self.route_payment(msg)
                return


            if self.payment.bob:
                node_alice = self.nodes[self.payment.node_alice]
                node_alice.add_msg(msg)
                return

        if msg.match_id in self.conf_data:
            data = self.conf_data[msg.match_id]
            if msg.check_list[0] == data.check_num:
                conf_msg = CheckMsg(msg.match_id,
                                   self.node_id, # useless ?
                                   msg.check_list[1:],
                                   msg.timestamp)
                node_to = self.nodes[data.from_id]
                node_to.add_msg(conf_msg)

            else:
                print("cheater detected?")
        
    def choose_match(self):
        #print(f"{self.node_id:02d} Choosing a match")
        if len(self.special_match_data) == 0:
            print("No matched seed found")
            return

        mini = max(match.fees for match in self.special_match_data.values())
        mini_id = [match.match_id for match 
                     in self.special_match_data.values() 
                     if match.fees == mini][0]

        match = self.special_match_data[mini_id]

        return match


    async def ant_route(self):
        while self.is_running:
            #  print(self.node_id, len(self.messages))
            if len(self.messages) != 0:
                msg = self.messages.pop(0)
                self._process_msg(msg)

           # Check and select matched seeds
            if (self.payment and 
                self.payment.alice and 
                len(self.special_match_data) > 0):
                #print(f'Alice got {len(self.special_match_data)} matches')
                #print("waiting to get more matches")

                t = get_timestamp() 
                phero = "0" + self.payment.seed
                try:
                    t_seed = self.phero_data[phero].timestamp
                except:
                    print(self.phero_data.keys())
                    print(phero)

                #t_seed = list(self.phero_data.values())[0].timestamp
                
                delta_t = (t - t_seed) % 256
                # Choose match after a bit
                        
                if (10 <= delta_t <= 80 and not self.payment.match):
                    print(f'Alice{self.node_id} got {len(self.special_match_data)} matches')
                 
                    # TODO test all paths ?
                    match = self.choose_match() 

                    self.payment.match = match

                    #TODO hack ??
                    node_bob = self.nodes[self.payment.node_bob]
                    node_bob.payment.match = match

                    self.handle_confirmation(match)
                   
                    
            await asyncio.sleep(self.delay)  

            #except Exception as e:
            #    print("Error: ", str(e))

    def route_payment(self, msg):
        match = self.payment.match
        t = get_timestamp()

        delta = (t - match.timestamp) % 256 
        fees_paid = self.payment.fees_max - match.fees

        sum_C = match.sum_counter
        c_0 = self.payment.c_0
        num_hops = sum_C - 2*c_0  
         
        print(f"Alice{self.node_id} paid {self.payment.amount} to Bob{self.payment.node_bob} with {fees_paid} fees in {delta/10}s with {num_hops+1} hops")

        # Consider payment done
        self.nodes[self.payment.node_bob].payment = None
        self.nodes[self.payment.node_alice].payment = None


    def start(self):
        self.is_running = True

    def stop(self):
        self.is_running = False

#

