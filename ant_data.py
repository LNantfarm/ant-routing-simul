#ANT DATA CLASSES
import asyncio 
from dataclasses import dataclass
from typing import List

    
@dataclass
class SeedData:
    amount: int
    timestamp: int
    fees0: int
    fees1: int
    counter0: int
    counter1: int
    sender0: int
    sender1: int
    pheromone0: bool = False
    pheromone1: bool = False

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
   # pheromone: str
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
        

@dataclass
class Payment:
    """Represents ant-routing payment data between Alice and Bob"""
    seed: str
    amount: int
    bob: bool
    alice: bool
    node_bob: int
    node_alice: int
    fees_max: int
    c_0: int
    check_list: list = None
    match: MatchData = None
    route: list = None
    paid: bool = False


class AntData:
    """
    Represents Ant Routing data objects needed to run the algorithms
    Data clear after some time
    """

    def __init__(self, lifetime=15, interval=0.1):
        """All data subtrees are empty"""
        self.lifetime = lifetime
        self.interval = interval
        self.numtrees = int(lifetime/interval)
        self.reset()

    def __repr__(self):
        return f"{self.phero}"
        
    def _get_data(self, datas, key):
        result = None
        for data in datas:
            if key in data.keys():
                result = data[key]
                break
        return result

    def add_pheromone(self, pheromone, data):
        """Adds new pheromone data to the latest subtree"""
        seed = pheromone[1:]
        self.phero[-1][seed] = data 

    def get_pheromone(self, pheromone):
        seed = pheromone[1:]
        p0 = pheromone[0] == '0'
        data = self._get_data(self.phero, seed)
        found = data and (p0 and data.pheromone0 or not p0 and data.pheromone1)
        return (found, data)

    def add_match(self, match_id, target):
        self.match[-1][match_id] = target

    def get_match(self, match_id):
        return self._get_data(self.match, match_id)

    def add_special_match(self, match_id, data):
        self.special_match[-1][match_id] = data

    def get_special_match(self, match_id):
        return self._get_data(self.special_match, match_id)
 
    def add_confirmation(self, match_id, data):
        self.confirmation[-1][match_id] = data

    def get_confirmation(self, match_id):
        return self._get_data(self.confirmation, match_id)
         
    async def clean_task(self):
        """Clears one subtree at regular interval"""
        while True:
            await asyncio.sleep(self.interval)
            for sub_data in (self.phero, self.confirmation, self.match, self.special_match):
                sub_data.pop(0)
                sub_data.append({})

    def reset(self):
        """Empties all subtrees""" 
        self.phero = [{} for _ in range(self.numtrees)]
        self.match = [{} for _ in range(self.numtrees)]
        self.confirmation = [{} for _ in range(self.numtrees)]
        self.special_match = [{} for _ in range(self.numtrees)]
        

async def tests():
    print("testing..")
    async def print_data(ant_data):
        while True:
            print(ant_data.phero)
            (f,d) = ant_data.get_pheromone("aaaa")
            if f: d.amount = 1337
            await asyncio.sleep(1)
 
    ant_data = AntData()
    sdata0 = SeedData(1, 1, 1, 1, 1, 1, 1, 1)
    sdata1 = SeedData(2, 2, 2, 2, 2, 2, 2, 2)
    ant_data.add_pheromone("aaaa", sdata0)
    ant_data.add_pheromone("bbbb", sdata1)

    tasks = [asyncio.create_task(print_data(ant_data)),
             asyncio.create_task(ant_data.clean_task())]
    await asyncio.gather(*tasks)
    print("Tests done")


if __name__ == "__main__":
    asyncio.run(tests())
