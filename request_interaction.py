from qns.entity.node.app import Application
from qns.entity.node.node import QNode
from qns.entity.cchannel.cchannel import ClassicChannel, ClassicPacket, RecvClassicPacket
from qns.entity.qchannel.qchannel import QuantumChannel
from qns.simulator.event import func_to_event, Event
from qns.simulator.simulator import Simulator
from qns.simulator.ts import Time
from qns.network.requests import Request
from qns.network.route.route import RouteImpl
from capacity_bb84 import BB84RecvApp, BB84SendApp


# def classify_request(net: QuantumNetwork):
# 将网络内的随机请求分类给对应的源节点(直接在产生请求的时候就把请求加入到对应源节点的请求队列中)
#    request_lists: list[Request] = net.requests
#    for re in request_lists:
#        src = re.src
#        index = int(src.name[1])
#        net.nodes[index].requests.append(re)
event_trigger = 3
time_trigger = 2    # second
request_times_restrict = 4


def out_delay(qchannel: QuantumChannel, restrict_time: dict, delay: int):
    # 判断限制是否真的无法满足请求，定时器
    flag = False
    t: Time = restrict_time[qchannel.name]
    s = qchannel._simulator
    if t < s.tc:
        return flag
    time_span = t - s.tc
    if time_span > Time(sec=delay):
        flag = True
    return flag


def restrict_is_real(qchannel: QuantumChannel, restrict_time: dict):
    t: Time = restrict_time[qchannel.name]
    s = qchannel._simulator
    if t < s.tc:
        return False
    return True


def has_no_restrict(path: tuple[float, QNode, list[QNode]], restrict: dict, restrict_time: dict):
    # 判断路径上是否存在限制link
    flag = True
    for i in range(0, len(path[2])-1):
        qchannel = path[2][i].get_qchannel(path[2][i+1])
        result = restrict[qchannel.name]    # 返回是否存在限制
        if result and restrict_is_real(qchannel, restrict_time):
            flag = False
            break
    return flag


def check_realizable(path: tuple[float, QNode, list[QNode]], restrict: dict, restrict_time: dict, delay: int):
    # 判断此条路径是否可行（是否存在不符合请求要求的link）
    flag = True
    for i in range(0, len(path[2])-1):
        qchannel = path[2][i].get_qchannel(path[2][i+1])
        result = restrict.get(qchannel.name)    # 返回是否存在限制
        if result and out_delay(qchannel, restrict_time, delay):
            flag = False
            break
    return flag


def if_already_in(already_accept: list[str], symbol: str = ""):
    accept_list = already_accept
    flag = False
    for item in accept_list:
        if item == symbol:
            flag = True
            break
    return flag


def search_app(sapps: list[BB84SendApp], rapps: list[BB84RecvApp], qchannel_name: str = ""):   # 得到qchannel对应的bb84app
    temps = None
    tempr = None
    for app in sapps:
        if app.qchannel.name == qchannel_name:
            temps = app
            break
    for app in rapps:
        if app.qchannel.name == qchannel_name:
            tempr = app
            break
    return temps, tempr


def get_info(send_app: BB84SendApp):    # 返回pool速率以及time
    s: Simulator = send_app.get_simulator()
    ts = s.ts
    tc = s.tc
    rate = len(send_app.succ_key_pool) / (tc-ts)
    time = send_app.time_flag
    if time < tc:
        time = tc
    time_span = time - tc
    return rate, time, time_span


def get_qchannel_list(node: QNode):
    link: list[QuantumChannel] = node.qchannels
    return link


def initialize(qchannels: list[QuantumChannel]):
    event = {}
    time = {}
    queue = {}
    for qchannel in qchannels:
        event[qchannel.name] = 0
        time[qchannel.name] = []    # 表示收到的请求的到达时间
        queue[qchannel.name] = []
    return event, time, queue


def queue_sort(queue: list):
    queue.sort(key=lambda s: s["key requirement"], reverse=True)    # from big to small and is stable
    queue.sort(key=lambda s: s["delay"])
    queue_up_times: list = []
    queue_down_temes: list = []
    for item in queue:
        temp = item["request times"]
        if temp < request_times_restrict:
            queue_down_temes.append(item)
        else:
            queue_up_times.append(item)
    queue_up_times.sort(key=lambda s: s["request times"], reverse=True)     # 没超过阈值，不需要按照路由次数排序
    sorted_queue = queue_up_times.extend(queue_down_temes)
    return sorted_queue


def create_request_info(management: dict, symbol: str, path: tuple[float, QNode, list[QNode]]):
    temp: dict = {}
    temp["flag"] = True     # 正常接收link的反馈，false代表此路径已不可行，对于answer“yes”，及时发包delete
    temp["list"] = []
    temp["path"] = path
    management[symbol] = temp


def update_request_info(node: QNode, management: dict, symbol: str):     # 把已经预留资源的链路取消锁定
    management[symbol]["flag"] = False
    for item in management[symbol]["list"]:
        src: QNode = item["src"]
        qchannel_name = item["aimed qchannel"]
        request_times = item["request times"]
        key_requirement = item["key requirement"]
        delay_tolerance = item["delay"]
        packet = ClassicPacket(msg={"aim": "delete", "symbol": symbol, "aimed qchannel": qchannel_name, "request times": request_times, "key requirement": key_requirement,
                                    "delay": delay_tolerance}, src=node, dest=src)
        cchannel: ClassicChannel = src.get_cchannel(node)     # route.query(node, src)
        cchannel.send(packet=packet, next_hop=src)
    management[symbol]["list"] = []


def check_if_is_over(mess: dict):
    flag = False
    if mess["flag"] and len(mess["list"]) == len(mess["path"][2])-1:
        temp = {}
        path = mess["path"]
        for i in range(0, len(path[2])-1):
            qchannel: QuantumChannel = path[2][i].get_qchannel(path[2][i+1])
            temp[qchannel.name] = False
        for item in mess["list"]:
            qchannel_name = item["aimed qchannel"]
            temp[qchannel_name] = True
        for i in range(0, len(path[2])-1):
            qchannel: QuantumChannel = path[2][i].get_qchannel(path[2][i+1])
            if temp[qchannel.name] is False:
                return flag
        flag = True
    return flag


class SendRequestApp(Application):
    def __init__(self, route: RouteImpl, restrict: dict, restrict_time: dict, request_management: dict, request_list: list[Request] = []):
        # 这里是量子网络的路由表， restrict代表当前节点维护的拓扑的限制信息
        super().__init__()
        self.request_list = request_list
        self.request_management = request_management
        self.restrict = restrict
        self.restrict_time = restrict_time
        self.route = route
        self.count = 0

    def install(self, node: QNode, simulator: Simulator):
        # 事件添加的顺序与处理的机制应该没有影响？
        super().install(node, simulator)
        # self.request_list.sort(Request.attr["start time"])
        for re in self.request_list:
            t = re.attr["start time"]+simulator.ts
            event = func_to_event(t, self.send_packet(re))
            self._simulator.add_event(event)

    def send_packet(self, re: Request):
        flag = False    # 是否有路径可以尝试发送
        route_result = self.route.query(re.src, re.dest)
        count = True
        index = float("inf")
        i = 0
        while i < len(route_result):  # 筛选出所有可行最短路径choice
            if route_result[i][0] > index:
                break
            if not check_realizable(route_result[i], self.restrict, self.restrict_time, re.attr["delay"]):  # 不可行
                del route_result[i]
                continue
            if count:
                index = route_result[i][0]  # 可行的最短路径长度
                count = False
            i += 1
        signal = False  # 是否找到目标路径
        for item in route_result:
            if item[0] > index:
                break
            if has_no_restrict(item, self.restrict, self.restrict_time):    # 存在一条没有限制的最短路径
                path = item
                flag = True
                signal = True
                break
        if not signal and len(route_result) > 0:
            flag = True
            path = route_result[0]
        if not flag:    # 没有路径可尝试
            print(f"{re.src.name}->{re.dest.name} is failed in serving currently: {re.attr}")
            return
        create_request_info(self.request_management, f"{self.get_node().name}-{self.count}", path)
        path_list: list = path[2]
        for i in range(1, len(path_list)):
            # 中间节点，假设经典网络是.all，请求信息均可一跳到达
            next_hop = path_list[i]     # next_hop = self.route.query(re.src, path_list[i])[0][1]
            cchannel: ClassicChannel = re.src.get_cchannel(next_hop)    # 找到传请求需要的经典link
            qchannel: QuantumChannel = path_list[i].get_qchannel(path_list[i-1])    # 找到需要预留资源的量子link
            packet = ClassicPacket(msg={"aim": "require", "symbol": f"{self.get_node().name}-{self.count}", "aimed qchannel": qchannel.name,  # f"{path_list[i-1].name}-{next_hop.name}",
                                        "key requirement": re.attr["key requirement"], "delay": re.attr["delay"], "request times": re.attr["request times"]}, src=re.src, dest=next_hop)   # dest=path_list[i]
            cchannel.send(packet=packet, next_hop=next_hop)
        self.count += 1


class RecvRequestApp(Application):
    def __init__(self, node: QNode, bb84rapps: list, bb84sapps: list, restrict: dict, restrict_time: dict, request_management: dict, already_accept: list = [], succ_request: list = []):
        # 已经接受可服务的，预留资源了
        super().__init__()
        self.already_accept = already_accept
        self.connect_bb84rapps = bb84rapps  # 知道与节点连接的所有link信息即可
        self.connect_bb84sapps = bb84sapps
        self.restrict = restrict
        self.restrict_time = restrict_time
        self.request_management = request_management
        self.succ_request = succ_request
        self.qchannels = get_qchannel_list(node)
        self.event_number_list, self.time_info, self.queue_list = initialize(self.qchannels)   # event strigger  time strigger  request queueing
        self.add_handler(self.handleClassicPacket, [RecvClassicPacket], [])

    def install(self, node: QNode, simulator: Simulator):   # 为每条qchannel创建初始时间触发事件
        t = simulator.ts
        str_t = t+Time(sec=time_trigger)
        for qchannel in self.qchannels:
            event = func_to_event(str_t, self.handletimer(qchannel.name))
            simulator.add_event(event)

    def handleClassicPacket(self, node: QNode, event: Event):
        # receive a classic packet，假设目的节点就是本节点，否则被前方的app转发走了
        if isinstance(event, RecvClassicPacket):
            packet = event.packet
            # get the packet message
            msg = packet.get()
            recv_time = event.t
            # handling the receiving packet
            aim_msg = msg["aim"]
            sym_msg = msg["symbol"]
            qchannel_name = msg["aimed qchannel"]
            request_times = msg["request times"]
            key_requirement = msg["key requirement"]
            delay_tolerance = msg["delay"]
            src = packet.src
            if aim_msg == "require":    # 中间节点
                flag = if_already_in(self.already_accept, sym_msg)   # 是否已经在准备服务的名单里
                if not flag:
                    temp: dict = {"symbol": sym_msg, "aimed qchannel": qchannel_name, "key requirement": key_requirement, "delay": delay_tolerance, "request times": request_times, "src": src}
                    self.queue_list[qchannel_name].append(temp)
                    self.event_number_list[qchannel_name] += 1
                    self.time_info[qchannel_name].append(recv_time)
                    t = recv_time+Time(sec=time_trigger)    # 加入对应时间触发事件
                    strigger = func_to_event(t, self.handletimer(qchannel_name))
                    self._simulator.add_event(strigger)
                    if self.event_number_list[qchannel_name] == event_trigger:  # 检查事件触发
                        self.event_number_list[qchannel_name] = 0
                        queue = self.queue_list[qchannel_name]
                        self.queue_list[qchannel_name] = []
                        self.distribution(queue, qchannel_name)
            elif aim_msg == "answer":   # 源节点
                content = msg["content"]
                if content == "yes":
                    # 先加入链路同意的列表，判断整条路径上的链路均同意了，再加入到already_accept
                    stamp: dict = self.request_management[sym_msg]
                    if stamp.get("flag"):
                        mass: dict = {"aimed qchannel": qchannel_name, "request times": request_times, "key requirement": key_requirement, "delay": delay_tolerance, "src": src}
                        stamp["list"].append(mass)
                        flag = check_if_is_over(self.request_management[sym_msg])
                        if flag:
                            dest = stamp["path"][2][-1]
                            attr: dict = {"key requirement": key_requirement, "delay": delay_tolerance, "request times": request_times}
                            re = Request(src=self._node, dest=dest, attr=attr)
                            self.succ_request.append(re)
                    else:       # 此路径不可行，立即让其释放资源
                        packet = ClassicPacket(msg={"aim": "delete", "symbol": sym_msg, "aimed qchannel": qchannel_name, "request times": request_times, "key requirement": key_requirement,
                                                    "delay": delay_tolerance}, src=self._node, dest=src)
                        cchannel: ClassicChannel = src.get_cchannel(self._node)     # route.query(self._node, src)
                        cchannel.send(packet=packet, next_hop=src)
                elif content == "no":
                    # update restrict in sendrequestapp and release resource of other agreed links
                    if self.restrict[qchannel_name] is True:
                        if self.restrict_time[qchannel_name] < msg["time flag"]:
                            self.restrict_time[qchannel_name] = msg["time flag"]
                    else:
                        self.restrict[qchannel_name] = True
                        self.restrict_time[qchannel_name] = msg["time flag"]
                    stamp: dict = self.request_management[sym_msg]
                    if stamp.get("flag"):
                        path = self.request_management[sym_msg]["path"]
                        dest = path[2][-1]
                        update_request_info(self._node, self.request_management, sym_msg)
                        simulator: Simulator = self.get_simulator
                        start_time = simulator.tc
                        attr: dict = {"start time": start_time, "key requirement": key_requirement, "delay": delay_tolerance, "request times": request_times+1}
                        re = Request(src=self._node, dest=dest, attr=attr)
                        t = re.attr["start time"]    # 重新寻路
                        node: QNode = self._node
                        app: Application = node.get_apps(SendRequestApp)
                        event = func_to_event(t, app.send_packet(re))
                        self._simulator.add_event(event)
            elif aim_msg == "delete":
                self.already_accept.remove(sym_msg)
                send_bb84, recv_bb84 = search_app(self.connect_bb84sapps, self.connect_bb84rapps, qchannel_name)    # time_flag and capacity
                rate, cur_time_tolerance, time_span = get_info(send_bb84)

    def distribution(self, queue: list, qchannel_name: str):
        sorted_queue = queue_sort(queue)
        for item in sorted_queue:
            key_requirement = item["key requirement"]
            delay_tolerance = item["delay"]
            send_bb84, recv_bb84 = search_app(self.connect_bb84sapps, self.connect_bb84rapps, qchannel_name)
            assert (send_bb84 is not None)
            assert (recv_bb84 is not None)
            sig = False
            cur_pool = send_bb84.current_pool
            if key_requirement <= cur_pool:  # 先看密钥池中的是否可以满足
                recv_bb84.current_pool -= key_requirement
                send_bb84.current_pool -= key_requirement
                sig = True
            else:
                recv_bb84.current_pool = 0
                send_bb84.current_pool = 0
                key_requirement_temp = key_requirement - cur_pool
                # 再看考虑未来产生的密钥
                rate, cur_time_tolerance, time_span = get_info(send_bb84)
                time_flag = cur_time_tolerance
                max_key = rate*(delay_tolerance - time_span)
                if key_requirement_temp <= max_key:  # 更新time_flag
                    sig = True
                    t = key_requirement_temp / rate
                    temp = Time(sec=t)
                    cur_time_tolerance += temp
                    send_bb84.time_flag = cur_time_tolerance
            aim_msg = "answer"
            sym_msg: str = item["symbol"]
            request_times = item["request times"]
            # sym = sym_msg.split("-")
            # node_name = sym[0]
            src_node: QNode = item["src"]
            if sig:
                self.already_accept.append(sym_msg)     # 加入到接受列表中
                content = "yes"
                packet = ClassicPacket(msg={"aim": aim_msg, "content": content, "symbol": sym_msg, "aimed qchannel": qchannel_name, "key requirement": key_requirement, "delay": delay_tolerance,
                                            "request times": request_times}, src=self._node, dest=src_node)
            else:
                content = "no"
                packet = ClassicPacket(msg={"aim": aim_msg, "content": content, "symbol": sym_msg, "aimed qchannel": qchannel_name, "key requirement": key_requirement, "delay": delay_tolerance,
                                            "request times": request_times, "time flag": time_flag}, src=self._node, dest=src_node)
            # next_hop = route.query(recv_bb84._node, src)
            next_hop = src_node
            cchannel: ClassicChannel = src_node.get_cchannel(self._node)
            cchannel.send(packet=packet, next_hop=next_hop)

    def handletimer(self, qchannel_name: str):
        if len(self.time_info[qchannel_name]) > 0:
            self.time_info[qchannel_name].pop(0)
        else:
            if self.event_number_list[qchannel_name] > 0:
                self.event_number_list[qchannel_name] = 0
                queue = self.queue_list[qchannel_name]
                self.queue_list[qchannel_name] = []
                self.distribution(queue, qchannel_name)
