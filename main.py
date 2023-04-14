# from qns.network.protocol import ClassicPacketForwardApp
from qns.network.network import QuantumNetwork
from capacity_bb84 import BB84RecvApp, BB84SendApp
from request_interaction import SendRequestApp, RecvRequestApp, start_time_order
from qns.entity.cchannel.cchannel import ClassicChannel
from qns.simulator.simulator import Simulator
from qns.network.topology import RandomTopology
from qns.network.topology.topo import ClassicTopology
from qns.network.route import DijkstraRouteAlgorithm
from create_request import random_requests
import numpy as np
import math


def drop_rate(length):   # 0.2db/km
    return 1-np.power(10, -length/50000)


end_simu_time = 100
q_length = 100  # 与drop_rate有关
c_length = 100
light_speed = 299791458
send_rate = 10
s_time = 0
e_time = end_simu_time - 90
s_request = 10
e_request = 200
s_delay = 10
e_delay = end_simu_time     # float('inf')
accuracy = 100000

for node_num in [100]:   # , 100, 150, 200, 250
    for i in range(2, 3):
        request_num = int(i * node_num)
        s = Simulator(0, end_simu_time, accuracy)
        topo = RandomTopology(nodes_number=node_num, lines_number=math.floor(node_num**2/4), qchannel_args={"delay": q_length / light_speed, "drop_rate": drop_rate(q_length)},
                              cchannel_args={"delay": c_length / light_speed})
        net = QuantumNetwork(topo=topo, route=DijkstraRouteAlgorithm(), classic_topo=ClassicTopology.All)
        #   print(net.qchannels)
        request_management = {}
        restrict = {}       # 初始化，所有节点维护的拓扑一致
        restrict_time = {}
        net_bb84rapps = {}
        net_bb84sapps = {}
        net_succ_request = {}
        net_fail_request = {}
        sendlist = []
        recvlist = []
        for node in net.nodes:
            net_bb84sapps[node.name] = []
            net_bb84rapps[node.name] = []
            net_succ_request[node.name] = []
            net_fail_request[node.name] = []
        for qchannel in net.qchannels:
            restrict[qchannel.name] = False
            (src, dest) = qchannel.node_list
            cchannel: ClassicChannel = src.get_cchannel(dest)
            send = BB84SendApp(dest=dest, qchannel=qchannel, cchannel=cchannel, send_rate=send_rate)
            recv = BB84RecvApp(src=src, qchannel=qchannel, cchannel=cchannel)
            sendlist.append(send)
            recvlist.append(recv)
            src.add_apps(send)
            dest.add_apps(recv)
            net_bb84sapps[src.name].append(send)
            net_bb84sapps[dest.name].append(send)
            net_bb84rapps[src.name].append(recv)
            net_bb84rapps[dest.name].append(recv)
        net.build_route()
        net_request = random_requests(nodes=net.nodes, number=request_num, start_time=s_time, end_time=e_time, start_request=s_request,
                                      end_request=e_request, start_delay=s_delay, end_delay=e_delay, allow_overlay=True)

        # print(net.requests)

        for node in net.nodes:
            start_time_order(net_request[node.name], 0, len(net_request[node.name])-1)
            sendre = SendRequestApp(net=net, node=node, restrict=restrict, restrict_time=restrict_time, request_management=request_management,
                                    fail_request=net_fail_request[node.name], request_list=net_request[node.name])
            recvre = RecvRequestApp(net=net, node=node, bb84rapps=net_bb84rapps[node.name], bb84sapps=net_bb84sapps[node.name], restrict=restrict, restrict_time=restrict_time,
                                    request_management=request_management, already_accept=[], succ_request=net_succ_request[node.name])
            node.add_apps(sendre)
            node.add_apps(recvre)
        net.install(s)
        #   print(net.qchannels)
        s.run()
        succ_number = 0
        fail_number = 0
        for node in net.nodes:
            for i in net_succ_request[node.name]:
                print(i, i.attr)
        for s in sendlist:
            print(len(s.succ_key_pool), s.current_pool)
        for r in recvlist:
            print(len(r.succ_key_pool), r.current_pool)

        print("successful!")
        for node in net.nodes:
            print(node.name, len(net_succ_request[node.name]))
            succ_number += 1
            # print(net_succ_request[node.name])
        print("failed!")
        for node in net.nodes:
            print(node.name, len(net_fail_request[node.name]))
            fail_number += 1
            # print(net_fail_request[node.name])
        print(succ_number, fail_number)
