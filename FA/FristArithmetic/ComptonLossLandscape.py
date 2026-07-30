# ComptonLossLandscape.py

import math


class ComptonLossLandscape:
    """
    ComptonEventScorer 的损失函数类。

    输入：
        ComptonEventScorer 对象

    职责：
        1. 根据 scorer.params 计算 loss；
        2. 根据训练标签计算 loss 对参数的梯度；
        3. 不负责更新参数，更新参数交给 Trainer。

    标签格式：
        labels = {
            event_index: 0 或 1,
            event_index: 0 或 1,
            ...
        }

    其中：
        y = 1 表示这个 candidate event 是真实正确事件；
        y = 0 表示错误组合 / 随机符合。
    """

    def __init__(
        self,
        scorer,
        positive_weight=1.0,
        negative_weight=1.0,
        lambda_rank=0.5,
        lambda_reg=1e-4,
        rank_margin=1.0,
    ):
        self.scorer = scorer

        self.positive_weight = positive_weight
        self.negative_weight = negative_weight

        self.lambda_rank = lambda_rank
        self.lambda_reg = lambda_reg
        self.rank_margin = rank_margin

    def compute_loss_and_gradient(self, labels):
        """
        计算总 loss 和总梯度。

        返回：
            total_loss, gradients

        gradients 是 dict：
            {
                参数名: 梯度值
            }
        """

        gradients = {
            name: 0.0
            for name in self.scorer.feature_names
        }

        bce_loss, bce_grad = self._bce_loss_and_gradient(labels)
        rank_loss, rank_grad = self._rank_loss_and_gradient(labels)
        reg_loss, reg_grad = self._regularization_loss_and_gradient()

        for name in gradients:
            gradients[name] = (
                bce_grad[name]
                + self.lambda_rank * rank_grad[name]
                + self.lambda_reg * reg_grad[name]
            )

        total_loss = (
            bce_loss
            + self.lambda_rank * rank_loss
            + self.lambda_reg * reg_loss
        )

        return total_loss, gradients

    def _bce_loss_and_gradient(self, labels):
        """
        Binary Cross Entropy loss。

        对单个 event：
            q = sigmoid(logit)
            L = - y log(q) - (1-y) log(1-q)

        梯度：
            dL/dtheta = (q - y) * feature
        """

        loss = 0.0

        gradients = {
            name: 0.0
            for name in self.scorer.feature_names
        }

        n_samples = 0

        for event_index, y in labels.items():
            event = self.scorer.event_list.get_event(event_index)

            features = self.scorer.extract_features(event)
            logit = self._calculate_logit(features)
            q = self.scorer._sigmoid(logit)

            sample_weight = (
                self.positive_weight
                if y == 1
                else self.negative_weight
            )

            eps = 1e-12

            sample_loss = -(
                y * math.log(q + eps)
                + (1 - y) * math.log(1 - q + eps)
            )

            loss += sample_weight * sample_loss

            for name in self.scorer.feature_names:
                gradients[name] += sample_weight * (q - y) * features[name]

            n_samples += 1

        if n_samples > 0:
            loss /= n_samples
            for name in gradients:
                gradients[name] /= n_samples

        return loss, gradients

    def _rank_loss_and_gradient(self, labels):
        """
        Ranking loss。

        对共享 hit 的冲突候选：
            如果 event_pos 是真候选，event_neg 是假候选，
            要求：

                logit_pos > logit_neg + margin

            loss:
                max(0, margin - logit_pos + logit_neg)

        这个 loss 专门服务于 EventMatcher：
            让真 event 在冲突候选中赢出来。
        """

        conflict_pairs = self._build_positive_negative_conflict_pairs(labels)

        loss = 0.0

        gradients = {
            name: 0.0
            for name in self.scorer.feature_names
        }

        if len(conflict_pairs) == 0:
            return loss, gradients

        for pos_index, neg_index in conflict_pairs:
            pos_event = self.scorer.event_list.get_event(pos_index)
            neg_event = self.scorer.event_list.get_event(neg_index)

            pos_features = self.scorer.extract_features(pos_event)
            neg_features = self.scorer.extract_features(neg_event)

            pos_logit = self._calculate_logit(pos_features)
            neg_logit = self._calculate_logit(neg_features)

            margin_violation = (
                self.rank_margin
                - pos_logit
                + neg_logit
            )

            if margin_violation <= 0:
                continue

            loss += margin_violation

            for name in self.scorer.feature_names:
                gradients[name] += (
                    -pos_features[name]
                    + neg_features[name]
                )

        n_pairs = len(conflict_pairs)

        loss /= n_pairs

        for name in gradients:
            gradients[name] /= n_pairs

        return loss, gradients

    def _regularization_loss_and_gradient(self):
        """
        L2 regularization。

        loss:
            sum(theta^2)

        gradient:
            2 theta
        """

        loss = 0.0

        gradients = {
            name: 0.0
            for name in self.scorer.feature_names
        }

        for name in self.scorer.feature_names:
            theta = self.scorer.params[name]
            loss += theta ** 2
            gradients[name] = 2.0 * theta

        return loss, gradients

    def _calculate_logit(self, features):
        """
        logit = sum(theta_i * x_i)
        """

        logit = 0.0

        for name in self.scorer.feature_names:
            logit += self.scorer.params[name] * features[name]

        return logit

    def _build_positive_negative_conflict_pairs(self, labels):
        """
        构建 ranking loss 需要的正负冲突对。

        返回：
            [(pos_index, neg_index), ...]
        """

        hit_to_events = {}

        for event_index in labels.keys():
            event = self.scorer.event_list.get_event(event_index)

            for hit_id in event.hit_ids:
                if hit_id not in hit_to_events:
                    hit_to_events[hit_id] = []
                hit_to_events[hit_id].append(event_index)

        pairs = set()

        for _, event_indexes in hit_to_events.items():
            positives = [
                idx for idx in event_indexes
                if labels[idx] == 1
            ]

            negatives = [
                idx for idx in event_indexes
                if labels[idx] == 0
            ]

            for pos in positives:
                for neg in negatives:
                    pairs.add((pos, neg))

        return list(pairs)