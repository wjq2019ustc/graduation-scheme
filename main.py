from qns.network.protocol import ClassicPacketForwardApp
from start_end_random import QuantumNetwork
from capacity_bb84 import BB84RecvApp, BB84SendApp
from request_interaction import SendRequestApp, RecvRequestApp
from qns.entity.cchannel.cchannel import ClassicChannel
from qns.simulator.simulator import Simulator
from qns.network.topology import RandomTopology
from qns.network.topology.topo import ClassicTopology
from qns.network.route import DijkstraRouteAlgorithm
from qns.network.route.route import RouteImpl
import numpy as np
import math


def drop_rate(length):   # 0.2db/km
    return 1-np.power(10, -length/50000)


end_simu_time = 10
q_length = 100000
c_length = 100000
light_speed = 299791458
send_rate = 1000
s_time = 0
e_time = end_simu_time
s_request = 10
e_request = 100
s_delay = 10
e_delay = float('inf')

for node_num in [50, 100, 150, 200, 250]:
    for i in range(1, 6):
        request_num = int(i * node_num / 2)
        s = Simulator(0, end_simu_time, 100000)
        topo = RandomTopology(nodes_number=node_num, lines_number=math.floor(node_num / 10), qchannel_args={"delay": q_length / light_speed, "drop_rate": drop_rate(q_length)},
                              cchannel_args={"delay": c_length / light_speed})
        net = QuantumNetwork(topo=topo, route=DijkstraRouteAlgorithm(), classic_topo=ClassicTopology.All)
        net.build_route()
        request_management = {}
        restrict = {}       # 初始化，所有节点维护的拓扑一致
        restrict_time = {}
        net_bb84rapps = {}
        net_bb84sapps = {}
        for node in net.nodes:
            net_bb84sapps[node.name] = []
            net_bb84rapps[node.name] = []
        for qchannel in net.qchannels:
            restrict[qchannel.name] = False
            (src, dest) = qchannel.node_list
            cchannel: ClassicChannel = src.get_cchannel(dest)
            send = BB84SendApp(dest=dest, qchannel=qchannel, cchannel=cchannel, send_rate=send_rate)
            recv = BB84RecvApp(src=src, qchannel=qchannel, cchannel=cchannel)
            src.add_apps(send)
            dest.add_apps(recv)
            net_bb84sapps[src.name].append(send)
            net_bb84sapps[dest.name].append(send)
            net_bb84rapps[src.name].append(recv)
            net_bb84rapps[dest.name].append(recv)
        route: RouteImpl = DijkstraRouteAlgorithm()
        net.random_requests(number=request_num, start_time=s_time, end_time=e_time, start_request=s_request, end_request=e_request, start_delay=s_delay, end_delay=e_delay, allow_overlay=True)
        for node in net.nodes:
            sendre = SendRequestApp(route=route, restrict=restrict, restrict_time=restrict_time, request_management=request_management, request_list=node.requests)
            recvre = RecvRequestApp(node=node, bb84rapps=net_bb84rapps[node.name], bb84sapps=net_bb84sapps[node.name], restrict=restrict, restrict_time=restrict_time,
                                    request_management=request_management, already_accept=[], succ_request=[])
            node.add_apps(sendre)
            node.add_apps(recvre)
        net.install(s)
        s.run()
