#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""slime_mold.py —— 黏菌混合策略（圆桌 + 图寻：聚合收敛 + 发散探索）。

依新目标：最可以同步类似黏菌（圆桌、图寻等可能）混合策略聚合发散检索。
黏菌（Physarum）隐喻：先发散探索多条路径（图寻），再按强度聚合收敛到最优路径（圆桌共识）。
纯标准库，Windows 直跑。
"""
import heapq


class SlimeMold:
    """圆桌 + 图寻混合：候选路径发散收集 → 按聚合强度收敛。"""

    def __init__(self):
        self.paths = []       # 候选路径（发散：图寻收集）
        self.consensus = None # 聚合收敛结果（圆桌）

    def explore(self, source, candidates):
        """发散：图寻——把 source 的邻接候选并入候选路径。"""
        for c in candidates:
            self.paths.append(c)

    def aggregate(self, weight_fn, top_k=1):
        """聚合：圆桌——按 weight_fn 评分，取强度最高的 top_k 为共识。"""
        scored = [(weight_fn(p), p) for p in self.paths]
        scored.sort(key=lambda x: -x[0])
        self.consensus = [p for _, p in scored[:top_k]]
        return self.consensus


class PhysarumGraph:
    """黏菌图寻：加权图 + Dijkstra 最短路径（Physarum 走迷宫：探索全路径 → 收敛最短）。"""

    def __init__(self):
        self.adj = {}   # node -> {neighbor: weight}

    def edge(self, a, b, w):
        self.adj.setdefault(a, {})[b] = w
        self.adj.setdefault(b, {})[a] = w

    def shortest_path(self, start, end):
        """Dijkstra：发散探索所有路径，收敛到最短路径。"""
        dist = {start: 0}
        prev = {}
        pq = [(0, start)]
        seen = set()
        while pq:
            d, u = heapq.heappop(pq)
            if u in seen:
                continue
            seen.add(u)
            if u == end:
                break
            for v, w in self.adj.get(u, {}).items():
                nd = d + w
                if nd < dist.get(v, float("inf")):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        if end not in dist:
            return None, None
        path, u = [], end
        while u != start:
            path.append(u)
            u = prev[u]
        path.append(start)
        return list(reversed(path)), dist[end]


if __name__ == "__main__":
    sm = SlimeMold()
    # 发散：图寻收集多条候选（例如检索"能量"相关的多条路径）
    sm.explore("root", ["科学·能量守恒", "哲学·生成", "艺术·留白", "科学·熵增"])
    # 聚合：圆桌按"与主题相关度"评分收敛到最优
    def relevance(p):
        score = 0
        if "能量" in p or "熵" in p:
            score += 2
        if "科学" in p:
            score += 1
        return score
    top = sm.aggregate(relevance, top_k=2)
    print("  候选路径 =", sm.paths)
    print("  聚合共识(top2) =", top, "（黏菌式发散→收敛）")

    # 黏菌走迷宫：加权图最短路径
    g = PhysarumGraph()
    for a, b, w in [("起点", "A", 2), ("起点", "B", 5), ("A", "终点", 3),
                    ("B", "终点", 1), ("A", "B", 1)]:
        g.edge(a, b, w)
    path, cost = g.shortest_path("起点", "终点")
    print("  黏菌迷宫最短路径 =", path, "代价 =", cost)
