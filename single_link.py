from capacity_bb84 import BB84RecvApp, BB84SendApp
from qns.entity.node.node import QNode
from qns.entity.qchannel.qchannel import QuantumChannel
from qns.entity.cchannel.cchannel import ClassicChannel
from qns.simulator.simulator import Simulator
from qns.network.requests import Request
import numpy as np


def drop_rate(length):   # 0.2db/km
    return 1-np.power(10, -length/50000)


q_length = 100000
c_length = 100000
light_speed = 299791458

n1 = QNode("n1")
n2 = QNode("n2")

q = QuantumChannel(name="q-n1-n2", length=q_length, delay=q_length / light_speed,
                   drop_rate=drop_rate(q_length))
# 引入了bit翻转，没有后处理，导致收发双方的密钥协商速率相差几乎一倍，对bit翻转进行处理
n1.add_qchannel(q)
n2.add_qchannel(q)
c = ClassicChannel(name="c-n1-n2", length=c_length, delay=c_length / light_speed)
n1.add_cchannel(c)
n2.add_cchannel(c)
s = BB84SendApp(n2, q, c, 2000)
r = BB84RecvApp(n1, q, c)
n1.add_apps(s)
n2.add_apps(r)
node: QNode = s.get_node()
print(node.name)

simu = Simulator(0, 10, 100000000000000)

n1.add_request(Request(src=n1, dest=n2, attr={"key requirement": 1000, "delay": 200}))

n1.install(simu)
n2.install(simu)

simu.run()
a = "n-1"
b = a.split("-")
print(a)
print(b)


class no():
    def __init__(self, a: dict) -> None:
        self.a = a
    
    def change(self):
        del self.a['a']
        print(self.a)


a = {'a': 1, 'b': 2, 'c': 1}
m = no(a)
m.change()
print(a)

print(q.name)