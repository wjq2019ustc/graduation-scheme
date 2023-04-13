from capacity_bb84 import BB84RecvApp, BB84SendApp
#   from qns.entity.node.node import QNode
#   from qns.entity.qchannel.qchannel import QuantumChannel
from qns.simulator.simulator import Simulator
#   from qns.network.requests import Request
#   from qns.network.route.route import RouteImpl
from request_interaction import SendRequestApp, RecvRequestApp, start_time_order
from qns.network.topology import LineTopology
from qns.network.network import QuantumNetwork
from qns.network.route import DijkstraRouteAlgorithm
from qns.network.topology.topo import ClassicTopology
from create_request import random_requests
import numpy as np


def drop_rate(length):   # 0.2db/km
    return 1-np.power(10, -length/50000)


q_length = 100
c_length = 100
light_speed = 299791458
end_simu_time = 100
send_rate = 6
s_time = 0
e_time = end_simu_time - 90
s_request = 300
e_request = 400
s_delay = 5
e_delay = end_simu_time-90    # float('inf')
accuracy = 100000

#   n1 = QNode("n1")
#   n2 = QNode("n2")
s = Simulator(0, end_simu_time, accuracy)
topo = LineTopology(nodes_number=2, qchannel_args={"delay": q_length / light_speed, "drop_rate": drop_rate(q_length)},
                    cchannel_args={"delay": c_length / light_speed})
net = QuantumNetwork(topo=topo, route=DijkstraRouteAlgorithm(), classic_topo=ClassicTopology.All)
#   cchannel is used to send basis info only, otherwise request packet will also be processed.

#   q = QuantumChannel(name="q-n1-n2", length=q_length, delay=q_length / light_speed,
#                      drop_rate=drop_rate(q_length))
# 引入了bit翻转，没有后处理，导致收发双方的密钥协商速率相差几乎一倍，对bit翻转进行处理
#   n1.add_qchannel(q)
#   n2.add_qchannel(q)
#   c = ClassicChannel(name="c-n1-n2", length=c_length, delay=c_length / light_speed)
#   n1.add_cchannel(c)
#   n2.add_cchannel(c)
#   s = BB84SendApp(n2, q, c, 2000)
#   r = BB84RecvApp(n1, q, c)
#   n1.add_apps(s)
#   n2.add_apps(r)

request_management = {}
restrict = {}       # 初始化，所有节点维护的拓扑一致
restrict_time = {}
net_bb84rapps = {}
net_bb84sapps = {}
net_succ_request = {}
net_fail_request = {}
#   net_bb84sapps[n1.name] = []
#   net_bb84rapps[n1.name] = []
#   net_succ_request[n1.name] = []
#   net_bb84sapps[n2.name] = []
#   net_bb84rapps[n2.name] = []
#   net_succ_request[n2.name] = []

#   net_bb84sapps[n2.name].append(s)
#   net_bb84sapps[n1.name].append(s)
#   net_bb84rapps[n2.name].append(r)
#   net_bb84rapps[n1.name].append(r)

#   route: RouteImpl = None
#   route.build([n1, n2], [q])

#   simu = Simulator(0, 1000000, 100000)

#   n1.add_request(Request(src=n1, dest=n2, attr={"key requirement": 1000, "delay": 200}))

#   sendre = SendRequestApp(net=net, restrict=restrict, restrict_time=restrict_time, request_management=request_management, request_list=node.requests)
#   recvre = RecvRequestApp(node=node, bb84rapps=net_bb84rapps[node.name], bb84sapps=net_bb84sapps[node.name], restrict=restrict, restrict_time=restrict_time,
#                           request_management=request_management, already_accept=[], succ_request=net_succ_request[node.name])
#   n1.install(simu)
#   n2.install(simu)

#   simu.run()
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
    cchannel = src.get_cchannel(dest)    # 与request所用channel分开xxxxxxxxxx
    #   src.add_cchannel(cchannel)
    #   dest.add_cchannel(cchannel)
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
net_request = random_requests(nodes=net.nodes, number=3, start_time=s_time, end_time=e_time, start_request=s_request, end_request=e_request,
                              start_delay=s_delay, end_delay=e_delay, allow_overlay=True)
#   返回一定数量的请求， 接下来分给对应节点
#   for j in range(len(net_request)):
#       i = net_request[j]
#       request_list[i.get("src").name].append(i)
#       print(i["src"], i["dest"], i["attr"])

for node in net.nodes:
    start_time_order(net_request[node.name], 0, len(net_request[node.name])-1)
    sendre = SendRequestApp(net=net, node=node, restrict=restrict, restrict_time=restrict_time, request_management=request_management,
                            fail_request=net_fail_request[node.name], request_list=net_request[node.name])   # , request_list=node.requests
    recvre = RecvRequestApp(net=net, node=node, bb84rapps=net_bb84rapps[node.name], bb84sapps=net_bb84sapps[node.name], restrict=restrict, restrict_time=restrict_time,
                            request_management=request_management, already_accept=[], succ_request=net_succ_request[node.name])
    node.add_apps(sendre)
    node.add_apps(recvre)
net.install(s)
s.run()

for node in net.nodes:
    for i in net_succ_request[node.name]:
        print(i, i.attr)

for s in sendlist:
    print(len(s.succ_key_pool), s.current_pool)
for r in recvlist:
    print(len(r.succ_key_pool), r.current_pool)

for node in net.nodes:
    print(node.name, len(net_succ_request[node.name]))
    # print(net_succ_request[node.name])

for node in net.nodes:
    print(len(net_fail_request[node.name]))
    # print(net_fail_request[node.name])
