# ComptonEventScorer.py

import json
import math
import numpy as np

from TwoHitEvent import TwoHitEvent
from ThreeHitEvent import ThreeHitEvent


class ComptonEventScorer:
    """
    康普顿候选事件可学习打分器。

    相比旧版本的核心变化（面向天基未知能谱场景）：

        1. 3-hit 的核心特征从裸的 delta_cos_second
           换成逐事件归一化的 pull（delta / sigma_delta）。
           pull 是能量和几何无关的统计量，跨事件可比。

        2. 删除了绝对能量特征（E_total_norm / E_mean_norm / E_max_norm）。
           天上能谱未知，打分器不应依赖绝对能量尺度；
           只保留能量"份额/形态"特征（E1_fraction、energy_balance）。

        3. 删除了类内自带的 fit()（与 ComptonGradientTrainer 重复，
           两条训练路径容易参数不同步）。
           训练统一走 ComptonGradientTrainer + ComptonLossLandscape。

    注意：
        没有 MC 真值之前不要训练。
        当前物理管线直接使用 event 构造时的解析分数
        （ThreeHitEvent 里基于 pull 的 score），
        本类留给 MC 数据到位后的监督学习阶段。

        旧版参数 json 与新特征表不兼容，不要 load 旧文件。
    """

    # pull 限幅：防止个别病态事件的巨大 pull 主导梯度
    PULL_CAP = 10.0

    def __init__(
        self,
        event_list,
        params=None,
        distance_scale_mm=100.0,
    ):
        self.event_list = event_list
        self.distance_scale_mm = distance_scale_mm

        self.feature_names = [
            "bias",

            # 事件类型相关
            "is_two_hit",
            "is_three_hit",

            # 基础物理合法性
            "is_physical",
            "layer_order_score",

            # 3-hit 主要打分依据：归一化 pull
            "abs_pull_second",
            "pull_second_squared",

            # 能量份额特征（能量尺度无关）
            "E1_fraction",
            "energy_balance",

            # 几何距离（作为几何可信度的补充信息）
            "distance_12_norm",
            "distance_23_norm",

            # 角度形态
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
        默认可学习参数（合理初始值，非最终答案）。

        设计意图：
            - abs_pull_second / pull_second_squared 为负：
              pull 越大（自洽性越差）分越低；
              这是 3-hit 的主要判据。
            - is_three_hit 为正、is_two_hit 为负：
              3-hit 有冗余约束可自证，先验更可信。
        """

        return {
            "bias": -1.0,

            "is_two_hit": -0.6,
            "is_three_hit": 1.0,

            "is_physical": 1.5,
            "layer_order_score": 0.4,

            "abs_pull_second": -0.8,
            "pull_second_squared": -0.10,

            "E1_fraction": 0.0,
            "energy_balance": 0.2,

            "distance_12_norm": -0.05,
            "distance_23_norm": -0.05,

            "abs_cos_theta_c_first": 0.0,
            "abs_cos_theta_g_second": 0.0,
        }

    # ============================================================
    # 2. 基础数学函数
    # ============================================================

    def _sigmoid(self, x):
        if x >= 0:
            return 1.0 / (1.0 + math.exp(-x))
        else:
            exp_x = math.exp(x)
            return exp_x / (1.0 + exp_x)

    def _safe_number(self, value, default=0.0):
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
        """

        is_two_hit = 1.0 if self._is_two_hit_event(event) else 0.0
        is_three_hit = 1.0 if self._is_three_hit_event(event) else 0.0

        is_physical = 1.0 if getattr(event, "is_physical", False) else 0.0

        layer_order_score = self._get_layer_order_score(event)

        # ---------- pull 特征（3-hit 专属）----------
        if is_three_hit:
            pull = getattr(event, "pull_second", None)

            if pull is None:
                # 兜底：老对象没有 pull 属性时用固定宽度归一化
                delta = self._safe_number(
                    getattr(event, "delta_cos_second", np.nan),
                    default=np.nan,
                )
                if np.isnan(delta):
                    pull = np.nan
                else:
                    pull = delta / 0.15

            if pull is None or not np.isfinite(pull):
                # 无法计算 pull 的 3-hit：给最大惩罚值
                abs_pull = self.PULL_CAP
            else:
                abs_pull = min(abs(float(pull)), self.PULL_CAP)

            abs_pull_second = abs_pull
            pull_second_squared = abs_pull ** 2
        else:
            abs_pull_second = 0.0
            pull_second_squared = 0.0

        # ---------- 能量份额特征 ----------
        E1_fraction = self._safe_number(
            getattr(event, "E1_fraction", 0.0)
        )

        energies = self._get_event_energies(event)

        E_max = max(energies) if len(energies) > 0 else 0.0
        E_min = min(energies) if len(energies) > 0 else 0.0

        if E_max > 0:
            energy_balance = E_min / E_max
        else:
            energy_balance = 0.0

        # ---------- 几何距离 ----------
        distance_12 = self._safe_number(getattr(event, "distance_12", 0.0))
        distance_23 = self._safe_number(getattr(event, "distance_23", 0.0))

        distance_12_norm = distance_12 / self.distance_scale_mm
        distance_23_norm = distance_23 / self.distance_scale_mm

        # ---------- 角度形态 ----------
        if hasattr(event, "cos_theta_c"):
            cos_theta_c_first = self._safe_number(event.cos_theta_c)
        else:
            cos_theta_c_first = self._safe_number(
                getattr(event, "cos_theta_c_first", 0.0)
            )

        abs_cos_theta_c_first = abs(cos_theta_c_first)

        if is_three_hit:
            abs_cos_theta_g_second = abs(
                self._safe_number(
                    getattr(event, "cos_theta_g_second", 0.0)
                )
            )
        else:
            abs_cos_theta_g_second = 0.0

        features = {
            "bias": 1.0,

            "is_two_hit": is_two_hit,
            "is_three_hit": is_three_hit,

            "is_physical": is_physical,
            "layer_order_score": layer_order_score,

            "abs_pull_second": abs_pull_second,
            "pull_second_squared": pull_second_squared,

            "E1_fraction": E1_fraction,
            "energy_balance": energy_balance,

            "distance_12_norm": distance_12_norm,
            "distance_23_norm": distance_23_norm,

            "abs_cos_theta_c_first": abs_cos_theta_c_first,
            "abs_cos_theta_g_second": abs_cos_theta_g_second,
        }

        return features

    def _get_event_energies(self, event):
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
        layers = getattr(event, "layers", [])

        if len(layers) == 0:
            return 0.0

        if layers == sorted(layers):
            return 1.0

        return 0.2

    # ============================================================
    # 5. 用当前参数给 event 打分
    # ============================================================

    def score_event(self, event):
        """
        计算：
            logit = sum(params[name] * features[name])
            score = sigmoid(logit)

        直接修改 event 对象。
        """

        features = self.extract_features(event)

        logit = 0.0

        for name in self.feature_names:
            logit += self.params[name] * features[name]

        score = self._sigmoid(logit)

        event.score = score
        event.learned_score = score
        event.score_logit = logit
        event.score_features = features
        event.scorer_name = self.__class__.__name__

        return score

    def score_all_events(self):
        for event in self.event_list.events:
            self.score_event(event)

        return self.event_list

    # ============================================================
    # 6. 保存 / 读取参数
    # ============================================================

    def save_params(self, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.params, f, indent=4)

    def load_params(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            params = json.load(f)

        missing = [
            name for name in self.feature_names
            if name not in params
        ]

        if len(missing) > 0:
            raise ValueError(
                "参数文件与当前特征表不兼容（可能是旧版本参数）。"
                f" 缺少: {missing}"
            )

        self.params = params

        return self.params

    def print_params(self):
        print("Current learnable parameters:")
        for name in self.feature_names:
            print(f"{name:28s}: {self.params[name]: .6f}")