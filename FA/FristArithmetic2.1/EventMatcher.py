# EventMatcher.py


class EventMatcher:
    """
    根据 EventList 中每个 event 的 score 进行全局 matching。

    输入：
        EventList 对象

    输出：
        直接修改 EventList：
            只保留被选中的 event
            删除与高分组合冲突的 event

    匹配原则：
        1. 同一个 hit 不能被多个 event 重复使用；
        2. 选择一组互不冲突的 event；
        3. 使总 score 最大。

    这本质上是 weighted set packing 问题。
    对 2-hit / 3-hit event 来说，就是小规模超图 matching。
    """

    def __init__(self, event_list, max_exact_events=28):
        self.event_list = event_list
        self.max_exact_events = max_exact_events

        self.selected_original_indexes = []
        self.removed_original_indexes = []

    def match(self):
        """
        主函数。

        将 EventList 中的 event 按冲突关系分成若干个 connected components。
        每个 component 内部独立求最优 matching。
        最后把所有 component 的结果合并。

        返回：
            修改后的 EventList。
        """

        components = self._build_conflict_components()

        selected_indexes = []

        for component in components:
            if len(component) <= self.max_exact_events:
                selected = self._solve_component_exact(component)
            else:
                selected = self._solve_component_greedy(component)

            selected_indexes.extend(selected)

        selected_indexes = sorted(selected_indexes)

        self.selected_original_indexes = selected_indexes
        self.removed_original_indexes = [
            idx for idx in self.event_list.indexes
            if idx not in selected_indexes
        ]

        self._rewrite_event_list(selected_indexes)

        return self.event_list

    def _event_hit_ids(self, event):
        """
        返回一个 event 使用的所有 hit_id。
        """

        return set(event.hit_ids)

    def _event_score(self, event):
        """Association score used for hit ownership, not imaging weight."""
        matching_score = float(getattr(event, "matching_score", 0.0))
        match_prob = float(getattr(event, "match_prob", 0.0))
        if matching_score != 0.0 or match_prob != 0.0:
            return matching_score
        return float(getattr(event, "score", 0.0))

    def _events_conflict(self, event_a, event_b):
        """
        判断两个 event 是否共享 hit。
        """

        hits_a = self._event_hit_ids(event_a)
        hits_b = self._event_hit_ids(event_b)

        return len(hits_a.intersection(hits_b)) > 0

    def _build_conflict_components(self):
        """
        按冲突关系把 event 分组。

        如果两个 event 共享 hit，则它们在同一个 conflict graph 里相连。
        每个 connected component 可以单独优化。
        """

        n_events = len(self.event_list)

        adjacency = {
            idx: set()
            for idx in range(n_events)
        }

        hit_to_events = {}

        for idx, event in enumerate(self.event_list.events):
            for hit_id in self._event_hit_ids(event):
                if hit_id not in hit_to_events:
                    hit_to_events[hit_id] = []
                hit_to_events[hit_id].append(idx)

        for _, event_indexes in hit_to_events.items():
            for i in event_indexes:
                for j in event_indexes:
                    if i != j:
                        adjacency[i].add(j)

        visited = set()
        components = []

        for idx in range(n_events):
            if idx in visited:
                continue

            stack = [idx]
            component = []
            visited.add(idx)

            while stack:
                current = stack.pop()
                component.append(current)

                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)

            components.append(component)

        return components

    def _solve_component_exact(self, component):
        """
        对一个 conflict component 做精确全局优化。

        用 branch and bound 搜索：
            每个 event 只有两个选择：
                选
                不选

        返回：
            最优选择的 event index 列表。
        """

        component = sorted(
            component,
            key=lambda idx: self._event_score(self.event_list.events[idx]),
            reverse=True,
        )

        suffix_upper_bound = self._build_suffix_upper_bound(component)

        best_score = 0.0
        best_selection = []

        def search(position, used_hits, current_score, current_selection):
            nonlocal best_score, best_selection

            if position >= len(component):
                if current_score > best_score:
                    best_score = current_score
                    best_selection = current_selection.copy()
                return

            # branch and bound:
            # 当前分数 + 后面所有正分 event 的理论最大分数
            # 如果仍然不可能超过 best_score，就剪枝。
            upper_bound = current_score + suffix_upper_bound[position]
            if upper_bound <= best_score:
                return

            event_index = component[position]
            event = self.event_list.events[event_index]

            event_score = self._event_score(event)
            event_hits = self._event_hit_ids(event)

            # 分支 1：选择这个 event
            if not event_hits.intersection(used_hits):
                new_used_hits = used_hits.union(event_hits)
                current_selection.append(event_index)

                search(
                    position + 1,
                    new_used_hits,
                    current_score + event_score,
                    current_selection,
                )

                current_selection.pop()

            # 分支 2：不选择这个 event
            search(
                position + 1,
                used_hits,
                current_score,
                current_selection,
            )

        search(
            position=0,
            used_hits=set(),
            current_score=0.0,
            current_selection=[],
        )

        return best_selection

    def _build_suffix_upper_bound(self, component):
        """
        为 branch and bound 构建上界。

        suffix_upper_bound[i] 表示：
            从 component[i] 到最后，所有正分 event 的分数总和。

        这是一个宽松上界，用来剪枝。
        """

        n = len(component)
        suffix = [0.0] * (n + 1)

        for i in range(n - 1, -1, -1):
            event = self.event_list.events[component[i]]
            score = max(0.0, self._event_score(event))
            suffix[i] = suffix[i + 1] + score

        return suffix

    def _solve_component_greedy(self, component):
        """
        大 component 的备用方案。

        当 component 太大时，精确搜索会变慢。
        这里使用 greedy 近似：
            按 score 从高到低选；
            与已选 event 冲突的丢弃。

        注意：
            greedy 不保证全局最优。
        """

        component = sorted(
            component,
            key=lambda idx: self._event_score(self.event_list.events[idx]),
            reverse=True,
        )

        selected = []
        used_hits = set()

        for event_index in component:
            event = self.event_list.events[event_index]
            event_hits = self._event_hit_ids(event)

            if self._event_score(event) <= 0.0:
                continue

            if event_hits.intersection(used_hits):
                continue

            selected.append(event_index)
            used_hits.update(event_hits)

        return selected

    def _rewrite_event_list(self, selected_indexes):
        """
        直接修改 EventList。

        只保留 selected_indexes 对应的 event。
        重新编号 indexes。
        """

        new_events = [
            self.event_list.events[idx]
            for idx in selected_indexes
        ]

        self.event_list.events = new_events
        self.event_list.indexes = list(range(len(new_events)))

    def get_selected_original_indexes(self):
        return self.selected_original_indexes

    def get_removed_original_indexes(self):
        return self.removed_original_indexes
