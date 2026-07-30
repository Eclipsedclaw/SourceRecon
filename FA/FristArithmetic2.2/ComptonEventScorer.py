# ComptonEventScorer.py

import json
import math
import numpy as np

from TwoHitEvent import TwoHitEvent
from ThreeHitEvent import ThreeHitEvent


class ComptonEventScorer:
    """
    康普顿候选事件可学习打分器。

    输入：
        EventList 对象

    功能：
        1. 自动识别 EventList 中的 TwoHitEvent 和 ThreeHitEvent；
        2. 提取每个 event 的特征；
        3. 用可学习参数 self.params 计算 event 的 score；
        4. 直接修改 event.score；
        5. 如果提供标签，可以训练 self.params。

    核心思想：
        score = sigmoid(参数 × 特征)

    其中：
        - 3-hit event 天然给更高分；
        - 2-hit event 天然给更低分；
        - 3-hit 的能量散射角和几何散射角差距越小，分数越高；
        - energy、distance、relative angle 等作为次要参考因素。
    """

    def __init__(
        self,
        event_list,
        params=None,
        energy_scale_mev=1.0,
        distance_scale_mm=100.0,
    ):
        """
        参数：
            event_list:
                EventList 对象，里面包含 TwoHitEvent / ThreeHitEvent 对象。

            params:
                可学习参数字典。
                如果为 None，则使用默认初始化参数。

            energy_scale_mev:
                能量归一化尺度。你的能量单位如果是 MeV，这里先取 1.0。

            distance_scale_mm:
                距离归一化尺度。你的坐标如果是 mm，这里先取 100 mm。
        """

        self.event_list = event_list
        self.energy_scale_mev = energy_scale_mev
        self.distance_scale_mm = distance_scale_mm

        self.feature_names = [
            "bias",

            # 事件类型相关
            "is_two_hit",
            "is_three_hit",

            # 基础物理合法性
            "is_physical",
            "layer_order_score",

            # 3-hit 主要打分依据
            "abs_delta_cos_second",
            "delta_cos_second_squared",

            # 能量相关次要因素
            "E_total_norm",
            "E_mean_norm",
            "E_max_norm",
            "energy_balance",

            # 几何距离相关次要因素
            "distance_12_norm",
            "distance_23_norm",

            # 角度相关次要因素
            "abs_cos_theta_c_first",
            "abs_cos_theta_g_second",
        ]

        if params is None:
            self.params = self._default_params()
        else:
            self.params = params

    # ============================================================
    # 1. 参数初始化
    # ============================================================

    def _default_params(self):
        """
        默认可学习参数。

        这些参数不是最终答案，只是一个合理的初始值。

        设计意图：
            - is_three_hit 为正：3-hit 起始分更高；
            - is_two_hit 为负：2-hit 起始分更低；
            - abs_delta_cos_second 为负：3-hit 的角度差越大，分越低；
            - delta_cos_second_squared 为负：大偏差进一步惩罚；
            - is_physical 为正：物理合法 event 加分；
            - layer_order_score 为正：正常层顺序加分。
        """

        return {
            "bias": -1.0,

            "is_two_hit": -0.4,
            "is_three_hit": 1.2,

            "is_physical": 1.0,
            "layer_order_score": 0.4,

            "abs_delta_cos_second": -3.0,
            "delta_cos_second_squared": -2.0,

            "E_total_norm": 0.0,
            "E_mean_norm": 0.1,
            "E_max_norm": 0.0,
            "energy_balance": 0.4,

            "distance_12_norm": -0.1,
            "distance_23_norm": -0.1,

            "abs_cos_theta_c_first": 0.0,
            "abs_cos_theta_g_second": 0.1,
        }

    # ============================================================
    # 2. 基础数学函数
    # ============================================================

    def _sigmoid(self, x):
        """
        sigmoid 函数，把任意实数映射到 0 到 1。
        """

        # 防止 exp 溢出
        if x >= 0:
            return 1.0 / (1.0 + math.exp(-x))
        else:
            exp_x = math.exp(x)
            return exp_x / (1.0 + exp_x)

    def _safe_number(self, value, default=0.0):
        """
        将 NaN / None 转成安全数字。
        """

        if value is None:
            return default

        try:
            if np.isnan(value):
                return default
        except TypeError:
            pass

        return float(value)

    # ============================================================
    # 3. 自动识别 event 类型
    # ============================================================

    def _is_two_hit_event(self, event):
        return isinstance(event, TwoHitEvent) or getattr(event, "n_hits", None) == 2

    def _is_three_hit_event(self, event):
        return isinstance(event, ThreeHitEvent) or getattr(event, "n_hits", None) == 3

    # ============================================================
    # 4. 提取 event 特征
    # ============================================================

    def extract_features(self, event):
        """
        从一个 TwoHitEvent 或 ThreeHitEvent 中提取打分特征。

        返回：
            features: dict
        """

        is_two_hit = 1.0 if self._is_two_hit_event(event) else 0.0
        is_three_hit = 1.0 if self._is_three_hit_event(event) else 0.0

        is_physical = 1.0 if getattr(event, "is_physical", False) else 0.0

        layer_order_score = self._get_layer_order_score(event)

        energies = self._get_event_energies(event)

        E_total = sum(energies)
        E_mean = np.mean(energies) if len(energies) > 0 else 0.0
        E_max = max(energies) if len(energies) > 0 else 0.0
        E_min = min(energies) if len(energies) > 0 else 0.0

        if E_max > 0:
            energy_balance = E_min / E_max
        else:
            energy_balance = 0.0

        E_total_norm = E_total / self.energy_scale_mev
        E_mean_norm = E_mean / self.energy_scale_mev
        E_max_norm = E_max / self.energy_scale_mev

        distance_12 = self._safe_number(
            getattr(event, "distance_12", 0.0)
        )

        distance_23 = self._safe_number(
            getattr(event, "distance_23", 0.0)
        )

        distance_12_norm = distance_12 / self.distance_scale_mm
        distance_23_norm = distance_23 / self.distance_scale_mm

        # 3-hit 的关键特征
        delta_cos_second = self._safe_number(
            getattr(event, "delta_cos_second", 0.0)
        )

        # 对 2-hit event，没有第二次散射角自洽性。
        # 因此这里将 delta 特征设为 0，由 is_two_hit / is_three_hit 控制基础差异。
        if is_two_hit:
            abs_delta_cos_second = 0.0
            delta_cos_second_squared = 0.0
        else:
            abs_delta_cos_second = abs(delta_cos_second)
            delta_cos_second_squared = delta_cos_second ** 2

        # 第一次康普顿角余弦
        if hasattr(event, "cos_theta_c"):
            cos_theta_c_first = self._safe_number(event.cos_theta_c)
        else:
            cos_theta_c_first = self._safe_number(
                getattr(event, "cos_theta_c_first", 0.0)
            )

        abs_cos_theta_c_first = abs(cos_theta_c_first)

        cos_theta_g_second = self._safe_number(
            getattr(event, "cos_theta_g_second", 0.0)
        )

        if is_two_hit:
            abs_cos_theta_g_second = 0.0
        else:
            abs_cos_theta_g_second = abs(cos_theta_g_second)

        features = {
            "bias": 1.0,

            "is_two_hit": is_two_hit,
            "is_three_hit": is_three_hit,

            "is_physical": is_physical,
            "layer_order_score": layer_order_score,

            "abs_delta_cos_second": abs_delta_cos_second,
            "delta_cos_second_squared": delta_cos_second_squared,

            "E_total_norm": E_total_norm,
            "E_mean_norm": E_mean_norm,
            "E_max_norm": E_max_norm,
            "energy_balance": energy_balance,

            "distance_12_norm": distance_12_norm,
            "distance_23_norm": distance_23_norm,

            "abs_cos_theta_c_first": abs_cos_theta_c_first,
            "abs_cos_theta_g_second": abs_cos_theta_g_second,
        }

        return features

    def _get_event_energies(self, event):
        """
        从 event 中提取能量列表。
        """

        energies = []

        if hasattr(event, "E1"):
            energies.append(self._safe_number(event.E1))

        if hasattr(event, "E2"):
            energies.append(self._safe_number(event.E2))

        if hasattr(event, "E3"):
            if event.E3 is not None:
                energies.append(self._safe_number(event.E3))
        return energies

    def _get_layer_order_score(self, event):
        """
        层顺序分数。

        正常顺序：
            ch0 -> ch1 -> ch2
            或 layer 编号递增

        给 1.0。

        非正常顺序给较低分。
        """

        layers = getattr(event, "layers", [])

        if len(layers) == 0:
            return 0.0

        if layers == sorted(layers):
            return 1.0

        return 0.2

    # ============================================================
    # 5. 用当前参数给一个 event 打分
    # ============================================================

    def score_event(self, event):
        """
        给单个 event 打分。

        计算：
            logit = sum(params[name] * features[name])
            score = sigmoid(logit)

        返回：
            score
        """

        features = self.extract_features(event)

        logit = 0.0

        for name in self.feature_names:
            logit += self.params[name] * features[name]

        score = self._sigmoid(logit)

        # 直接修改 event 对象
        event.score = score
        event.learned_score = score
        event.score_logit = logit
        event.score_features = features
        event.scorer_name = self.__class__.__name__

        return score

    def score_all_events(self):
        """
        给 EventList 中所有 event 打分。

        这个函数会直接修改 event_list 里每一个 event 的 score。
        """

        for event in self.event_list.events:
            self.score_event(event)

        return self.event_list

    # ============================================================
    # 6. 训练可学习参数
    # ============================================================

    def fit(self, labels, epochs=200, learning_rate=0.05, verbose=True):
        """
        训练 self.params。

        参数：
            labels:
                dict，格式为：
                    {
                        event_index: 0 或 1,
                        event_index: 0 或 1,
                        ...
                    }

                y = 1 表示该候选 event 是真实康普顿事件；
                y = 0 表示该候选 event 是错误组合 / 随机符合。

            epochs:
                训练轮数。

            learning_rate:
                学习率。

        注意：
            labels 通常来自 Geant4 / Monte Carlo 真值。
            真实实验数据如果没有真值，就不能直接监督训练。
        """

        for epoch in range(epochs):
            total_loss = 0.0

            # 梯度累加
            grads = {
                name: 0.0
                for name in self.feature_names
            }

            n_samples = 0

            for event_index, y in labels.items():
                event = self.event_list.get_event(event_index)

                features = self.extract_features(event)

                logit = 0.0
                for name in self.feature_names:
                    logit += self.params[name] * features[name]

                q = self._sigmoid(logit)

                # BCE loss
                eps = 1e-12
                loss = -(
                    y * math.log(q + eps)
                    + (1 - y) * math.log(1 - q + eps)
                )

                total_loss += loss

                # logistic regression 的梯度：
                # dL/dtheta = (q - y) * x
                for name in self.feature_names:
                    grads[name] += (q - y) * features[name]

                n_samples += 1

            if n_samples == 0:
                raise ValueError("labels 为空，无法训练 ComptonEventScorer。")

            # 参数更新
            for name in self.feature_names:
                grads[name] /= n_samples
                self.params[name] -= learning_rate * grads[name]

            avg_loss = total_loss / n_samples

            if verbose and (epoch % 20 == 0 or epoch == epochs - 1):
                print(f"epoch {epoch:4d} | loss = {avg_loss:.6f}")

        # 训练结束后，用新参数重新给所有 event 打分
        self.score_all_events()

        return self.params

    # ============================================================
    # 7. 保存 / 读取参数
    # ============================================================

    def save_params(self, filepath):
        """
        保存当前可学习参数。
        """

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.params, f, indent=4)

    def load_params(self, filepath):
        """
        读取已经训练好的参数。
        """

        with open(filepath, "r", encoding="utf-8") as f:
            self.params = json.load(f)

        return self.params

    def print_params(self):
        """
        打印当前参数，方便检查。
        """

        print("Current learnable parameters:")
        for name in self.feature_names:
            print(f"{name:28s}: {self.params[name]: .6f}")