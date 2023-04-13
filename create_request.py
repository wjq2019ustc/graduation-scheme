
from qns.utils.rnd import get_randint, get_rand
from qns.simulator.ts import Time
from qns.entity import QNode
from qns.network.requests import Request


def random_requests(nodes: list[QNode], number: int, start_time: float, end_time: float, start_request: int = 0, end_request: int = 2000, start_delay: float = 0, end_delay: float = float('inf'),
                    allow_overlay: bool = False):
    # 修改：加入了请求下发时间、请求密钥量以及延时要求
    used_nodes: list[int] = []
    nnodes = len(nodes)
    request_list = {}
    for node in nodes:
        request_list[node.name] = []
    
    if number < 1:
        raise QNSNetworkError("number of requests should be large than 1")

    if not allow_overlay and number * 2 > nnodes:
        raise QNSNetworkError("Too many requests")

    for n in nodes:
        n.clear_request()

    for i in range(number):
        while True:
            src_idx = get_randint(0, nnodes - 1)
            dest_idx = get_randint(0, nnodes - 1)
            if src_idx == dest_idx:
                continue
            if not allow_overlay and src_idx in used_nodes:
                continue
            if not allow_overlay and dest_idx in used_nodes:
                continue
            if not allow_overlay:
                used_nodes.append(src_idx)
                used_nodes.append(dest_idx)
            break
        
        attr: dict = {}
        src = nodes[src_idx]
        dest = nodes[dest_idx]
        t = get_rand(start_time, end_time)
        attr["start time"] = Time(sec=t)
        re = get_randint(start_request, end_request)
        attr["key requirement"] = re
        de = get_rand(start_delay, end_delay)
        attr["delay"] = de
        attr["request times"] = 1
        req = Request(src=src, dest=dest, attr=attr)
        # request_list[i]["src"] = src
        # request_list[i]["dest"] = dest
        # request_list[i]["attr"] = attr
        # self.add_request(src, dest, attr)
        # src.add_request(req)
        # print(re.attr for re in src.requests)
        # dest.add_request(req)
        print(src, dest, req.attr)
        request_list[src.name].append(req)
    #   for node in nodes:
    #       for i in request_list[node.name]:
    #           print(i.src, i.dest, i.attr)
    return request_list


class QNSNetworkError(Exception):
    pass
