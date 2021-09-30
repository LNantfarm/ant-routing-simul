"""Ant Routing Algorithm"""
#TODO stop node after N payments finished
#TODO generate random payment async
#TODO Network class: sample node with large distance etc


import random
import asyncio
import networkx as nx
import matplotlib.pyplot as plt

from ant_testing import Node
from ant_network import Network

N = 119
P = 0.02
N_PAYMENTS = 6
SHOW = True

async def create_batch_payments(pay_nodes):
    for (a, b) in pay_nodes:
        amount = random.randint(1000,9999)
        print(f'Alice{a.node_id} pays {amount} to Bob{b.node_id}')
        await asyncio.sleep(2*random.random())
        a.pay(amount, b.node_id)

async def create_random_payment(g, node_objects):
    found = False
    while not found:
        ab = random.sample(list(g.nodes), 2) 
        found = not g.has_edge(*ab)

    return ab

async def main():
    """Start ant routing nodes"""

    network = Network(N)
    tmp = nx.fast_gnp_random_graph(N, P)

    subs = list(sorted(nx.connected_components(tmp), key=len, reverse=True))
    g = tmp.subgraph(subs[0]).copy()

    g = nx.relabel_nodes(g, { node:i for i,node in enumerate(g.nodes)})

    nodes = list(g.nodes)

    lengths = list(nx.all_pairs_shortest_path_length(g))
    dists = []
    dist_max = 0
    for node_id,node_dists in lengths:
        dist_max = 0
        for k,v in node_dists.items():
            if v > dist_max:
                dist_max = v
        dists.append(dist_max)

    try:
        max_dist = sorted(dists, reverse=True)[N//10]
    except Exception as e:
        print(dists)
        max_dist = dist_max
    print(f'Distance is {max_dist}')
    alice = nodes[dists.index(max_dist)]
    endpoints = [ k for k,v in lengths[alice][1].items() if v == dists[alice]]
    bob = endpoints[0]

    sample_nodes = random.sample(list(set(nodes) - {alice, bob}), 2*N_PAYMENTS)
    pay_nodes_id = [(alice, bob)]
    for i in range(N_PAYMENTS):
        ab = (sample_nodes[2*i], sample_nodes[2*i+1])
        pay_nodes_id.append(ab)

    sample_nodes.extend([alice, bob])

    for edge in pay_nodes_id:
        try:
            g.remove_edge(edge[0], edge[1])
        except Exception as error:
            pass

    print(f"alice: {alice}", list(g.neighbors(alice)))
    print(f"bob: {bob}", list(g.neighbors(bob)))

    for (a,b) in pay_nodes_id:
        dist = nx.shortest_path_length(g, a, b)
        print(f"Alice{a} and Bob{b} at distance {dist}")

    node_objects = [Node(node, set(g.neighbors(node))) for node in nodes]


    print(await create_random_payment(g, node_objects))

    #Labels
    labels = {}
    for node in g.nodes:
        labels[node] = f"{node_objects[node].fee}"

    if SHOW:
        nx.draw(g, 
                node_color=["yellow" if node in sample_nodes else "green"
                    for node in nodes ],
                with_labels=True)

        #pos = nx.spring_layout(g) 
        #nx.draw(g, pos, 
        #        node_color=["yellow" if node in sample_nodes else "green"
        #            for node in nodes ],
        #        with_labels=True)

        #shifted_pos = {k:[v[0],v[1]+ .08] for k,v in pos.items()}

        #nx.draw_networkx_labels(g, pos=shifted_pos, labels=labels, font_size=10)

        plt.show(block=False)
        plt.pause(0.01)
        #nx.draw(g)
        #plt.show()


    pay_nodes = list(map(
        lambda x: (node_objects[x[0]], node_objects[x[1]]),
            pay_nodes_id))

    for node in node_objects:
        node.set_nodes(node_objects)

    node_alice = node_objects[alice]

    for node in node_objects:
        node.start()

    
    tasks = [asyncio.create_task(create_batch_payments(pay_nodes))]
    for node in node_objects:
        task = asyncio.create_task(node.ant_route())
        tasks.append(task)

    await asyncio.gather(*tasks)

    print("## Ant routing done ##")


asyncio.run(main())
