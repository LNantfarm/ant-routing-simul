import networkx as nx
import matplotlib.pyplot as plt
import random
import hashlib
import asyncio

from ant_utils import get_timestamp
from ant_testing import PheroData, PheroMsg, Node, Payment
import math

N = 42
p = 0.069
tmp = nx.fast_gnp_random_graph(N, p)
SHOW = True

subs = list(sorted(nx.connected_components(tmp), key=len, reverse=True))
g = tmp.subgraph(list(subs[0])).copy()

g = nx.relabel_nodes(g, { node:i for i,node in enumerate(g.nodes)})

nodes = list(g.nodes)

lengths = list(nx.all_pairs_shortest_path_length(g))
dists = []
for node_id,node_dists in lengths:
    dist_max = 0
    for k,v in node_dists.items():
        if v > dist_max:
            dist_max = v
    dists.append(dist_max)

try:
    max_dist = sorted(dists, reverse=True)[N//10]
except:
    print(dists)
    max_dist = dist
print(f'Distance is {max_dist}')
alice = nodes[dists.index(max_dist)]
endpoints = [ k for k,v in lengths[alice][1].items() if v == dists[alice]]
bob = endpoints[0]

try:
    g.remove_edge(alice, bob)
except:
    #print("No channel between A and B")
    pass

print(f"alice: {alice}", list(g.neighbors(alice)))
print(f"bob: {bob}", list(g.neighbors(bob)))
#print("common neighbors: ", set(g.neighbors(alice)) & set(g.neighbors(bob))) 
       
#define node data?

if SHOW:
    nx.draw(g, 
            node_color=["yellow" if node in (bob, alice) else "green"
                for node in nodes ],
            with_labels=True)

    plt.show(block=False)
    plt.pause(0.01)
    #nx.draw(g) 
    #plt.show()


async def main():
    seed_ab = 'beef'
    amount = 1337
    c_0 = random.randint(64,128)

    node_objects = [Node(node, set(g.neighbors(node))) for node in nodes]

    for node in node_objects: node.set_nodes(node_objects)

    node_bob = node_objects[bob]
    node_alice = node_objects[alice]

    payment_alice = Payment(
            seed_ab,
            amount,
            False,
            True,
            node_bob,
            node_alice,
            node_bob.maxfees + node_alice.maxfees,
            c_0,
            )
    payment_bob = Payment(
            seed_ab,
            amount,
            True,
            False,
            node_bob,
            node_alice,
            node_bob.maxfees + node_alice.maxfees,
            c_0,
            )
    
    node_bob.set_payment(payment_bob)
    node_alice.set_payment(payment_alice)

    for node in node_objects:
        node.start()

    tasks = []
    for node in node_objects:
        task = asyncio.create_task(node.ant_route())
        tasks.append(task)
        
   # for node in node_objects:
   #     print(node)

    await asyncio.gather(*tasks)

    print("## Ant routing done ##")


asyncio.run(main())


