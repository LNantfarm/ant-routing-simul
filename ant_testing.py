#ANT ROUTING LIB
import asyncio 
import random
import time

from dataclasses import dataclass
from ant_utils import get_timestamp, seed_bar
from typing import List

@dataclass
class PheroData:
    seed: str
    counter: int
    from_id: int
    fees_remaining: int
    amount: int
    timestamp: int

@dataclass
class PheroMsg:
    seed: str
    counter: int
    from_id: int
    fees_remaining: int
    amount: int
    timestamp: int


@dataclass
class MatchData:
    match_id: int
    from_id: int
    sum_counter: int
    fees: int
    timestamp:int

@dataclass
class MatchMsg:
    seed: str
    match_id: int
    from_id: int
    counter: int
    sum_counter: int
    fees: int
    timestamp: int

@dataclass
class ConfData:
    match_id: int
    from_id: int
    check_num: int
    timestamp: int

@dataclass
class ConfMsg:
    match_id: int
    from_id: int
    check_list: list
    timestamp: int

@dataclass
class CheckMsg:
    match_id: int
    from_id: int
    check_list: int
    timestamp: int
        
#TODO ADD PAY FUNCTION AND PAYMENT CLASS?
#     TO HANDLE DATA

class Node:
    pass

@dataclass
class Payment:
    """Represents ant-routing payment data between Alice and Bob"""
    seed: str
    amount: int
    bob: bool
    alice: bool
    node_bob: Node
    node_alice: Node
    fees_max: int
    c_0: int
    check_list: list = None
    match: MatchData = None
    route: list = None
    paid: bool = False

matches = 0

class Node:
    """ Represents a Lightning node
        with data for ant routing""" 

    def __init__(self, node_id, peers):
        # Node id and local topology
        self.node_id = node_id
        self.peers = peers
        self.messages = []
        self.delay = random.random()/10
        self.fee   = random.randint(10,30)
        self.maxfees = random.randint(250,300)
        self.balance = random.randint(50,300)*100

        
        self.payment = None
        
        # Memory data
        self.phero_data = dict()
        self.match_data = dict()
        self.conf_data = dict()
        self.check_data = dict()
        self.special_match_data = dict()

        self.is_running = False


    def __repr__(self):
        return f'Node({self.node_id}, {set(self.peers)})'

    def _process_msg(self, msg):
        #print(f'{self.node_id}: {msg.__class__.__name__} @ {msg.timestamp}')
        
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

    def set_payment(self, payment):
        self.payment = payment
        bit = "0" if self.payment.alice else "1"
        msg = PheroMsg(
            bit + self.payment.seed,
            self.payment.c_0 - 1, #so that they send c_0 to neighbors
            self.node_id,
            self.payment.fees_max // 2,
            self.payment.amount,
            get_timestamp()
        )

        self.add_msg(msg)


    def add_msg(self, msg):
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
        print(f"Handling check\n {self.node_id}, ", end="")
        # Only Alice
        len_checks = len(msg.check_list) - len(self.payment.check_list) 
        match =  self.special_match_data[msg.match_id]
        sum_C = match.sum_counter
        c_0 = self.payment.c_0
        if sum_C - 2*c_0 - len_checks != 0:
            print("cheater detected TODO")
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
                        msg.timestamp
                        )

        if not msg.seed in self.phero_data:
            if fees_remaining >= 0:
                self.phero_data[msg.seed] = new_data
            else:
                print("fees too high")
                return 
        else:
            prev_data = self.phero_data[msg.seed]
            if prev_data.counter <= msg.counter:
                return

            if fees_remaining >= 0:
                self.phero_data[msg.seed] = new_data
            else:
                print("fees too high")
                pass
                    
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
                        msg.timestamp
                        )

                    node.add_msg(new_data)                    
        else:
            self.create_and_send_match(msg.seed)


    def process_match(self, msg):
        # print(f"{self.node_id} got match {msg}")
        if msg.seed[1] == "0":
            p0 = msg.seed[1:]
            if p0 in self.phero_data:
                p0_data = self.phero_data[p0]
                if p0_data.counter != msg.counter - 1:
                    return

                #if s=0 ? what does it mean?
                if self.payment and self.payment.bob:
                    print("matched reached bob")

                if self.payment and self.payment.alice: 
                    match = MatchData(msg.match_id,
                                  msg.from_id,
                                  msg.sum_counter,
                                  msg.fees,
                                  msg.timestamp
                                  ) 

                    #What if match already there ?
                    if msg.match_id in self.special_match_data:
                        print("WARNING: overwriting match")
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

                    if self.payment and self.payment.bob:
                        print("matched reached bob")

                    self.nodes[p0_data.from_id].add_msg(match_msg)
                    
        else: # msg.seed[1] == "1":
            p1 = msg.seed[1:]
            if p1 in self.phero_data:
                p1_data = self.phero_data[p1]
                if p1_data.counter != msg.counter - 1:
                    return

                self.match_data[msg.match_id] = p1_data.from_id

            #TODO why zero ?? leaks info ?
            #TODO what id several payments? need dict by seed
            if not self.payment:

                match_msg = MatchMsg(msg.seed,
                                msg.match_id,
                                self.node_id,
                                msg.counter - 1,
                                msg.sum_counter,
                                msg.fees,
                                msg.timestamp)

                self.nodes[p1_data.from_id].add_msg(match_msg)


    def process_conf(self, msg):
        #print(f"node {self.node_id} got conf")

        # If bob or alice ?
        if self.payment and self.payment.bob: 
            self.payment.node_alice.add_msg(msg)
            return
        
        if self.payment and self.payment.alice:
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


    def process_check(self, msg):
        #print(f"{self.node_id} got check")

        if self.payment and self.payment.alice:
            self.route_payment()
            return

        print(self.node_id, end=", ")

        if self.payment and self.payment.bob:
            print()
            self.payment.node_alice.add_msg(msg)
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
        print("Choosing a match")
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
            if (self.payment and len(self.special_match_data) > 0):
                #print(f'Alice got {len(self.special_match_data)} matches')
                #print("waiting to get more matches")

                t = get_timestamp() 
                t_seed = list(self.phero_data.values())[0].timestamp
                delta_t = (t - t_seed) % 256
                # Choose match after a bit
                        
                if (10 <= delta_t <= 40 and
                    not self.payment.match and
                    self.payment and 
                    len(self.special_match_data) > 0):
                    print(f'Alice got {len(self.special_match_data)} matches')
                 
                    # TODO test all paths ?
                    match = self.choose_match()
                    
                    self.payment.match = match
                    self.handle_confirmation(match)
                   
                    
            await asyncio.sleep(self.delay)  

            #except Exception as e:
            #    print("Error: ", str(e))

    def route_payment(self):
        match = self.payment.match
        t = get_timestamp()

        delta = (t - match.timestamp) % 256 
        
        print("Payment info:")
        print(f" Match selected:\n  {match}")
        print(f" fees: {self.payment.fees_max - match.fees} ")
        print(f" matching time: {delta/10}s")



    def start(self):
        self.is_running = True

    def stop(self):
        self.is_running = False


