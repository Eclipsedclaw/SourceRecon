# ComptonSupervisedTrainerV2.py

import math


class ComptonSupervisedTrainerV2:
    """
    用 Geant4 truth 训练 ComptonEventScorerV2。

    loss:
        L = BCE(match_prob, y_match)
            + lambda_full * y_match * BCE(full_prob, y_full)

    注意：
        full_deposition 只对 y_match=1 的 candidate 有意义。
    """

    def __init__(
        self,
        scorer,
        learning_rate=0.05,
        lambda_full=1.0,
        lambda_reg=1e-4,
    ):
        self.scorer = scorer
        self.learning_rate = learning_rate
        self.lambda_full = lambda_full
        self.lambda_reg = lambda_reg
        self.loss_history = []

    def fit(self, epochs=100, verbose=True):
        for epoch in range(epochs):
            loss, grad_match, grad_full = self._loss_and_gradients()

            for name in self.scorer.feature_names:
                self.scorer.match_params[name] -= (
                    self.learning_rate * grad_match[name]
                )
                self.scorer.full_params[name] -= (
                    self.learning_rate * grad_full[name]
                )

            self.scorer.score_all_events()
            self.loss_history.append(loss)

            if verbose and (epoch % 10 == 0 or epoch == epochs - 1):
                print(f"epoch {epoch:4d} | loss = {loss:.6f}")

        return self.scorer

    def _sigmoid(self, x):
        return self.scorer._sigmoid(x)

    def _bce(self, q, y):
        eps = 1e-12
        return -(
            y * math.log(q + eps)
            + (1 - y) * math.log(1 - q + eps)
        )

    def _loss_and_gradients(self):
        grad_match = {name: 0.0 for name in self.scorer.feature_names}
        grad_full = {name: 0.0 for name in self.scorer.feature_names}

        total_loss = 0.0
        n = 0

        for event in self.scorer.event_list.events:
            y_match = getattr(event, "y_match", None)

            if y_match is None:
                continue

            features = self.scorer.extract_features(event)

            match_logit = self.scorer._logit(
                features,
                self.scorer.match_params,
            )
            full_logit = self.scorer._logit(
                features,
                self.scorer.full_params,
            )

            q_match = self._sigmoid(match_logit)
            q_full = self._sigmoid(full_logit)

            loss = self._bce(q_match, y_match)

            for name in self.scorer.feature_names:
                grad_match[name] += (q_match - y_match) * features[name]

            y_full = getattr(event, "y_full", None)

            if y_match == 1 and y_full is not None:
                loss_full = self._bce(q_full, y_full)
                loss += self.lambda_full * loss_full

                for name in self.scorer.feature_names:
                    grad_full[name] += (
                        self.lambda_full
                        * (q_full - y_full)
                        * features[name]
                    )

            total_loss += loss
            n += 1

        if n == 0:
            raise RuntimeError("没有可训练样本：所有 event 的 y_match 都是 None。")

        for name in self.scorer.feature_names:
            grad_match[name] /= n
            grad_full[name] /= n

            grad_match[name] += (
                self.lambda_reg * 2.0 * self.scorer.match_params[name]
            )
            grad_full[name] += (
                self.lambda_reg * 2.0 * self.scorer.full_params[name]
            )

        total_loss /= n

        return total_loss, grad_match, grad_full