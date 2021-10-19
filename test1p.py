import asyncio
import random 
import time

from ant_network import Network
from ant_utils import lifespan

NUM_NODES = 50
N_PAY_DELAY = 0.2


def pay_stats(payment_list):
    durations = list(map(lambda p: p.duration, payment_list))
    if len(durations) == 0:
        return None

    max_duration = max(durations)
    min_duration = min(durations)
    num_payments = len(payment_list)
    return (max_duration, min_duration, sum(durations)/len(durations), num_payments)


async def test_payloop(network):
    payments = create_all_payments(network)
    payments = payments[:1]*10
    print(payments)
    print(f"{len(payments)} created!")
    start_time = time.monotonic()
    while len(payments) != 0:
        found = False
        for _ in range(len(payments)):
            (alice, bob) = payments.pop(0)
            node_alice = network.nodes[alice]
            amount = random.randint(1000,10000)
            found = node_alice.pay(amount, bob)
            if not found:
                payments.append((alice, bob))
            else: 
                #print(" "*80 + f"# {len(payments)} to go!")
                await asyncio.sleep(0.01)

       # await asyncio.sleep(N_PAY_DELAY + 0*random.random()/100)

        await asyncio.sleep(10)
        payments_stats = map(pay_stats, [node.paid_list for node in network.nodes])
        total_msgs = 0
        total_payments = 0
        for i, stat in enumerate(payments_stats):
            node = network.nodes[i]
            if stat is not None:
                (maxi, mini, avg, num) = stat
                print(f"Node{i} got {num} payments in average time {avg/10:.2f}s (max={maxi/10:.1f}s, min={mini/10:.1f}s)")
                total_payments += num

            print(f"  n{i}: total_msg={node.total_messages} msg_processed={node.processed_messages}")

            total_msgs += node.total_messages

        total_time = time.monotonic() - start_time
        print(f"{total_payments} payments using {total_msgs} msgs in {total_time:.2f}s")

        for node in network.nodes: 
            node.ant_data.reset()   
            node.msgs = []
            node.total_messages = 0
            node.processed_messages = 0

    print("All payments done!")

        
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
 
    print('end')
    network.show()

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

async def random_test(network):
    while True:
        stats = network.stats()
        
        payments = [node.payment for node in network.nodes]
        num_pending = sum(map(lambda x: 1 if x else 0, payments))
        lifespans = list(map(lambda x: round(lifespan(x)/10,1) if x else 0, payments))

        def print_stat(i):
            return f"max={stats[i][0]}\tsum={stats[i][1]}"
        
        if True:
            print("#"*50 + '\n' + 
                f"###   pheromones:   {print_stat(0)}\n" +  
                f"###   matches:      {print_stat(1)}\n" +
                f"###   confirmation: {print_stat(2)}\n" + 
                f"###   spec.matches: {print_stat(3)}\n" + 
                f"###   pending: {num_pending}/{network.num_nodes}\n" +  
                    "#"*50 )
            print(sorted(set(lifespans), reverse=True)) 
        
        await asyncio.sleep(12)


async def test(network):
    tasks = network.create_tasks()
    tasks.append(asyncio.create_task(test_payloop(network)))
    tasks.append(asyncio.create_task(random_test(network)))

    await asyncio.gather(*tasks)
    print("Test done")

if __name__ == "__main__":
    network = Network(NUM_NODES, 3/NUM_NODES)
    #network.show()
    try:
        asyncio.run(test(network))
    except KeyboardInterrupt:
        print("bye!")
        exit(42)
    except SystemExit:
        network.show()
        exit()

