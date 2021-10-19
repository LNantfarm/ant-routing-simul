import asyncio
import random 
import time

from ant_network import Network
from ant_utils import lifespan


NUM_NODES = 10
N_PAY_DELAY = 0.005

class ETestDone(Exception):
    pass


ntype = { 'PheroMsg': 0, 'MatchMsg': 2, 'ConfMsg': 3, 'CheckMsg': 4 }

def index_msg(msg):
    t = msg.__class__.__name__ 
    result = ntype[t]
    if result == 0:
        result = int(msg.pheromone[0])
    
    return result

async def test_payloop(network):
    payments = create_all_payments(network)
    payments = [payments[0]]
    
    start_time = time.monotonic()
    while len(payments) != 0:
        found = False
        for _ in range(len(payments)):
            (alice, bob) = payments.pop(0)
            node_alice = network.nodes[alice]
            amount = random.randint(1000,9999)
            found = node_alice.pay(amount, bob)
            if not found:
                payments.append((alice, bob))
            else: 
                #print(" "*80 + f"# {len(payments)} to go!")
                await asyncio.sleep(0.01)

        await asyncio.sleep(N_PAY_DELAY + 0*random.random()/100)

    await asyncio.sleep(5)

    def pay_stats(payment_list):
        durations = list(map(lambda p: p.duration, payment_list))
        if len(durations) == 0:
            return None

        max_duration = max(durations)
        min_duration = min(durations)
        num_payments = len(payment_list)
        return (max_duration, min_duration, sum(durations)/len(durations), num_payments)


    payments_stats = map(pay_stats, [node.paid_list for node in network.nodes])
    total_msgs = 0
    total_payments = 0
    msgs_counts = [0,0,0,0,0] #Phero, Match, Conf, Check
    for i, stat in enumerate(payments_stats):
        node = network.nodes[i]
        if stat is not None:
            (maxi, mini, avg, num) = stat
            #print(f"Node{i} got {num} payments in average time {avg/10:.2f}s (max={maxi/10:.1f}s, min={mini/10:.1f}s)")
            #print(f"  total_msg={node.total_messages} msg_processed={node.processed_messages}")

            total_payments += num

        total_msgs += node.total_messages
        
        counts = [0,0,0,0,0]
        for msg in node.msgs:
            counts[index_msg(msg)] += 1
            msgs_counts[index_msg(msg)] += 1
        node.msg_types = counts
        print(f"{node.node_id:03d}: p={counts[0] + counts[1]:03d} ({counts[0]:03d}+{counts[1]:03d}) m={counts[2]:03d} cc=[{counts[-2:]}] peers={len(node.peers):02d} matched={node.created:03d}")


    total_time = time.monotonic() - start_time
    print(f"{total_payments} payments using {total_msgs} msgs in {total_time}s")
    print(msgs_counts)
    print(f'{msgs_counts[0] + msgs_counts[1]} msgs, {len(network.g.edges)} edges')    

    network.show()
         
    matches = {}
    for node in network.nodes:
        for seed in node.seedmatches:
            if seed in matches:
                matches[seed].extend(node.seedmatches[seed])
            else: 
                matches[seed] = node.seedmatches[seed]
    
    for seed in matches.keys():
        #print(seed, len(matches[seed]))
        pass
 
    raise ETestDone


async def test_payloop_(network):
    while True:
        (alice, bob, amount) = create_random_payment(network)
        if alice != None: 
            print(f'Alice{alice.node_id:02d} pays {amount:04d} to Bob{bob:02d}')
            alice.pay(amount, bob)
        await asyncio.sleep(N_PAY_DELAY + random.random())
         

def create_random_payment(network):
    found = False
    count = 0
    while not found:
        count += 1
        [alice, bob] = random.sample(list(network.g.nodes), 2) 
        found = not network.g.has_edge(alice, bob)
        node_alice = network.nodes[alice]
        node_bob = network.nodes[bob]
        found &= not node_bob.is_busy()
        found &= not node_alice.is_busy()
        if count > 10: 
            return (None, None, None)


    amount = random.randint(1000,10000)
    node_alice = network.nodes[alice]
    return (node_alice, bob, amount)
    return (network.nodes[0], 1, 10000)

def create_all_payments(network):
    payments = []
    for alice in network.g.nodes:
        for bob in network.g.nodes:
            if alice == bob: continue
            if network.g.has_edge(alice, bob):
                continue
            payments.append((alice, bob))
    
    random.shuffle(payments)
    return payments


async def test():
    for num_nodes in range(10,101, 10):
        num_nodes = 37
        network = Network(num_nodes, 8/num_nodes)
        #print(f"{len(network.g.edges)} edges, {len(network.g.nodes)} nodes")
        #network.show()

        tasks = network.create_tasks()
        tasks.extend([test_payloop(network)]) #, random_test(network)])

        tasks = [ task if isinstance(task, asyncio.Task) else asyncio.create_task(task) for task in tasks ]
    
        network.tasks = tasks

        try:
            await asyncio.gather(*tasks)
        except ETestDone:
            for task in tasks:
                task.cancel()


    print("Test done")
    await asyncio.sleep(10)

if __name__ == "__main__":
    #network = Network(NUM_NODES, 8/NUM_NODES)
    #network.show()
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("bye!")
        exit(42)
    except SystemExit:
        network.show()
        exit()

