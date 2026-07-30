import math


class ComptonSupervisedTrainerV2:
    """Train same-gamma association and candidate full-absorption heads."""

    def __init__(
        self,
        scorer,
        learning_rate=0.05,
        lambda_full=1.0,
        lambda_reg=1e-4,
        match_positive_weight=1.0,
        full_positive_weight=1.0,
    ):
        self.scorer = scorer
        self.learning_rate = learning_rate
        self.lambda_full = lambda_full
        self.lambda_reg = lambda_reg
        self.match_positive_weight = match_positive_weight
        self.full_positive_weight = full_positive_weight
        self.loss_history = []
        self.match_loss_history = []
        self.full_loss_history = []

    def fit(self, epochs=100, verbose=True):
        for epoch in range(epochs):
            result = self._loss_and_gradients()
            loss, match_loss, full_loss, grad_match, grad_full = result

            for name in self.scorer.feature_names:
                self.scorer.match_params[name] -= (
                    self.learning_rate * grad_match[name]
                )
                self.scorer.full_params[name] -= (
                    self.learning_rate * grad_full[name]
                )

            self.scorer.score_all_events()
            self.loss_history.append(loss)
            self.match_loss_history.append(match_loss)
            self.full_loss_history.append(full_loss)

            if verbose and (epoch % 10 == 0 or epoch == epochs - 1):
                print(
                    "epoch {0:4d} | total={1:.6f} | match={2:.6f} "
                    "| full_absorption={3:.6f}".format(
                        epoch,
                        loss,
                        match_loss,
                        full_loss,
                    )
                )
        return self.scorer

    @staticmethod
    def _bce(probability, label):
        eps = 1e-12
        return -(
            label * math.log(probability + eps)
            + (1 - label) * math.log(1 - probability + eps)
        )

    def _loss_and_gradients(self):
        names = self.scorer.feature_names
        grad_match = {name: 0.0 for name in names}
        grad_full = {name: 0.0 for name in names}

        match_loss_sum = 0.0
        full_loss_sum = 0.0
        match_weight_sum = 0.0
        full_weight_sum = 0.0

        for event in self.scorer.event_list.events:
            y_match = getattr(event, "y_same_gamma", None)
            if y_match is None:
                y_match = getattr(event, "y_match_correct", None)
            if y_match is None:
                y_match = getattr(event, "y_match", None)
            if y_match is None:
                continue

            features = self.scorer.extract_features(event)
            match_logit = self.scorer._logit(
                features,
                self.scorer.match_params,
            )
            q_match = self.scorer._sigmoid(match_logit)
            match_weight = (
                self.match_positive_weight if y_match == 1 else 1.0
            )
            match_loss_sum += match_weight * self._bce(q_match, y_match)
            match_weight_sum += match_weight
            for name in names:
                grad_match[name] += (
                    match_weight * (q_match - y_match) * features[name]
                )

            # Full absorption is meaningful only for a same-gamma candidate.
            y_full = getattr(event, "y_full_absorption", None)
            if y_full is None:
                y_full = getattr(event, "y_complete_full", None)
            if y_match == 1 and y_full is not None:
                full_logit = self.scorer._logit(
                    features,
                    self.scorer.full_params,
                )
                q_full = self.scorer._sigmoid(full_logit)
                full_weight = (
                    self.full_positive_weight if y_full == 1 else 1.0
                )
                full_loss_sum += full_weight * self._bce(q_full, y_full)
                full_weight_sum += full_weight
                for name in names:
                    grad_full[name] += (
                        full_weight * (q_full - y_full) * features[name]
                    )

        if match_weight_sum == 0:
            raise RuntimeError("没有可训练的 match 样本。")
        if full_weight_sum == 0:
            raise RuntimeError(
                "没有可训练的 full-absorption 样本；请检查 truth 能量和候选标签。"
            )

        match_loss = match_loss_sum / match_weight_sum
        full_loss = full_loss_sum / full_weight_sum

        for name in names:
            grad_match[name] /= match_weight_sum
            grad_full[name] = (
                self.lambda_full * grad_full[name] / full_weight_sum
            )
            grad_match[name] += (
                2.0 * self.lambda_reg * self.scorer.match_params[name]
            )
            grad_full[name] += (
                2.0 * self.lambda_reg * self.scorer.full_params[name]
            )

        total_loss = match_loss + self.lambda_full * full_loss
        return total_loss, match_loss, full_loss, grad_match, grad_full
