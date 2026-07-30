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
        validation_event_list=None,
        early_stopping_patience=60,
        early_stopping_min_delta=1e-5,
    ):
        self.scorer = scorer
        self.learning_rate = learning_rate
        self.lambda_full = lambda_full
        self.lambda_reg = lambda_reg
        self.match_positive_weight = match_positive_weight
        self.full_positive_weight = full_positive_weight
        self.validation_event_list = validation_event_list
        self.early_stopping_patience = int(early_stopping_patience)
        self.early_stopping_min_delta = float(early_stopping_min_delta)
        self.loss_history = []
        self.match_loss_history = []
        self.full_loss_history = []
        self.validation_loss_history = []
        self.best_epoch = None
        self.best_validation_loss = None

    def fit(self, epochs=500, verbose=True):
        best_match_params = self.scorer.match_params.copy()
        best_full_params = self.scorer.full_params.copy()
        epochs_without_improvement = 0

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

            validation_loss = None
            if self.validation_event_list is not None:
                validation_loss, _, _ = self._evaluate_loss(
                    self.validation_event_list
                )
                self.validation_loss_history.append(validation_loss)

                improved = (
                    self.best_validation_loss is None
                    or validation_loss
                    < self.best_validation_loss
                    - self.early_stopping_min_delta
                )
                if improved:
                    self.best_validation_loss = validation_loss
                    self.best_epoch = epoch
                    best_match_params = self.scorer.match_params.copy()
                    best_full_params = self.scorer.full_params.copy()
                    epochs_without_improvement = 0
                else:
                    epochs_without_improvement += 1

            if verbose and (epoch % 10 == 0 or epoch == epochs - 1):
                message = (
                    "epoch {0:4d} | train_total={1:.6f} "
                    "| train_match={2:.6f} | train_full={3:.6f}".format(
                        epoch, loss, match_loss, full_loss
                    )
                )
                if validation_loss is not None:
                    message += " | validation={:.6f}".format(validation_loss)
                print(message)

            if (
                self.validation_event_list is not None
                and epochs_without_improvement
                >= self.early_stopping_patience
            ):
                print(
                    "early stopping at epoch {0}; best epoch={1}, "
                    "best validation loss={2:.6f}".format(
                        epoch,
                        self.best_epoch,
                        self.best_validation_loss,
                    )
                )
                break

        if self.validation_event_list is not None:
            self.scorer.match_params = best_match_params
            self.scorer.full_params = best_full_params
            self.scorer.score_all_events()
            print(
                "restored best validation checkpoint: epoch={0}, "
                "loss={1:.6f}".format(
                    self.best_epoch,
                    self.best_validation_loss,
                )
            )
        return self.scorer

    def _evaluate_loss(self, event_list):
        match_losses = []
        full_losses = []

        for event in event_list.events:
            y_match = getattr(event, "y_same_gamma", None)
            if y_match is None:
                continue

            features = self.scorer.extract_features(event)
            match_logit = self.scorer._logit(
                features,
                self.scorer.match_params,
            )
            match_weight = (
                self.match_positive_weight if y_match == 1 else 1.0
            )
            match_losses.append(
                (
                    match_weight
                    * self._bce(self.scorer._sigmoid(match_logit), y_match),
                    match_weight,
                )
            )

            y_full = getattr(event, "y_full_absorption", None)
            if y_match == 1 and y_full is not None:
                full_logit = self.scorer._logit(
                    features,
                    self.scorer.full_params,
                )
                full_weight = (
                    self.full_positive_weight if y_full == 1 else 1.0
                )
                full_losses.append(
                    (
                        full_weight
                        * self._bce(self.scorer._sigmoid(full_logit), y_full),
                        full_weight,
                    )
                )

        if not match_losses or not full_losses:
            raise RuntimeError(
                "validation set must contain labelled match and "
                "full-absorption samples"
            )

        match_loss = sum(item[0] for item in match_losses) / sum(
            item[1] for item in match_losses
        )
        full_loss = sum(item[0] for item in full_losses) / sum(
            item[1] for item in full_losses
        )
        total_loss = match_loss + self.lambda_full * full_loss
        return total_loss, match_loss, full_loss

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
