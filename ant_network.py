import networkx as nx
import random
import matplotlib.pyplot as plt
import asyncio
from math import sqrt

from ant_node import Node


ntype = { 'PheroMsg': 0, 'MatchMsg': 2, 'ConfMsg': 3, 'CheckMsg': 4 }

def index_msg(msg):
    t = msg.__class__.__name__ 
    result = ntype[t]
    if result == 0:
        result = int(msg.pheromone[0])
    
    return result


class Network:
    """Implements a random network of nodes"""

    def __init__(self, num_nodes, p=None):
        self.num_nodes = num_nodes
        if p is None: 
            self.p = 1./num_nodes
        else: 
            self.p = p
        self.new(num_nodes, self.p)

    def new(self, num_nodes=0, p=None):
        if num_nodes != 0:
            self.num_nodes = num_nodes
            if p is None: 
                self.p = 1./num_nodes

        # Create new graph and keep largest connected component
        tmp = nx.fast_gnp_random_graph(self.num_nodes, self.p)
        subs = list(sorted(nx.connected_components(tmp), key=len, reverse=True))
        self.g = tmp.subgraph(subs[0]).copy()
        self.g = nx.relabel_nodes(self.g, { node:i for i,node in enumerate(self.g.nodes)})


        #self.g = nx.grid_graph(dim=(int(sqrt(num_nodes)), int(sqrt(num_nodes))))
        #self.g = nx.relabel_nodes(self.g, { node:i for i,node in enumerate(self.g.nodes)})

        # WARNING num_nodes is not the one passed in args
        self.num_nodes = len(self.g.nodes)

        self.nodes = [Node(node, set(self.g.neighbors(node))) for node in tuple(self.g.nodes)]

        for node in self.nodes:
            node.set_nodes(self.nodes)

    def show(self):
        colors = [ "green" for node in self.g.nodes ]
        colors = []
        matches = []
        num_msgs = []
        for node in self.nodes:
            matches.append(len(list(filter(lambda m: index_msg(m) == 2, node.msgs))))
            num_msgs.append(len(node.msgs))

        matchs_created = [ node.created for node in self.nodes ]

        colors=num_msgs
        print(colors)

        nx.draw(self.g, 
                node_color=colors,
                with_labels=True)

        plt.show()

    def create_tasks(self):
        tasks = []
        for node in self.nodes:
            node.start()

            #route_task = asyncio.create_task(node.ant_route())
            #clean_task = asyncio.create_task(node.ant_data.clean_task())
            tasks.extend([node.ant_route(), node.ant_data.clean_task()])
#            tasks.extend([route_task, clean_task])
            
        return tasks

    def stats(self):
        sizes = [node.ant_data.get_sizes() for node in self.nodes]
        s_zip = list(zip(*sizes))
        result = []
        for stat in s_zip:
            sum_sizes = max(map(lambda x: x[0], stat))
            max_sizes = max(map(lambda x: x[1], stat))
        
            result.append((max_sizes, sum_sizes))
            
        return result

async def do_tests():
    num_nodes = 100
    network = Network(num_nodes)

    async def check():
        while True:
            node = random.randint(1, network.num_nodes)
            if network.nodes[node].is_running:
                print(f"node {node} is running")
            
            await asyncio.sleep(2)


    tasks = network.create_tasks()
    tasks.append(asyncio.create_task(check()))
    await asyncio.gather(*tasks)
    print("done")


if __name__ == "__main__":
    asyncio.run(do_tests())


