# ComptonGradientTrainer.py

from ComptonLossLandscape import ComptonLossLandscape


class ComptonGradientTrainer:
    """
    ComptonEventScorer 的梯度下降训练器。

    输入：
        ComptonEventScorer 对象

    职责：
        1. 调用 ComptonLossLandscape 计算 loss 和 gradients；
        2. 用梯度下降更新 scorer.params；
        3. 每次更新后重新给 EventList 中所有 event 打分。
    """

    def __init__(
        self,
        scorer,
        loss_landscape=None,
        learning_rate=0.05,
    ):
        self.scorer = scorer
        self.learning_rate = learning_rate

        if loss_landscape is None:
            self.loss_landscape = ComptonLossLandscape(scorer)
        else:
            self.loss_landscape = loss_landscape

        self.loss_history = []

    def fit(self, labels, epochs=200, verbose=True):
        """
        训练 scorer.params。

        参数：
            labels:
                dict:
                    {
                        event_index: 0 或 1
                    }

            epochs:
                训练轮数。
        """

        for epoch in range(epochs):
            loss, gradients = self.loss_landscape.compute_loss_and_gradient(
                labels
            )

            self._update_params(gradients)

            self.scorer.score_all_events()

            self.loss_history.append(loss)

            if verbose and (epoch % 20 == 0 or epoch == epochs - 1):
                print(f"epoch {epoch:4d} | loss = {loss:.6f}")

        return self.scorer

    def _update_params(self, gradients):
        """
        普通梯度下降：

            theta = theta - learning_rate * gradient
        """

        for name in self.scorer.feature_names:
            self.scorer.params[name] -= (
                self.learning_rate * gradients[name]
            )

    def get_loss_history(self):
        return self.loss_history