from scipy.stats import norm
import numpy as np


# Defining class for the light simulation
class EqualSplit:
    def __init__(self, no_of_arms, profits, rng):
        self.policy_name = "EqualSplit"
        self.no_of_arms = no_of_arms
        self.profit_per_order = np.array(profits)           # Profit per order for each arm (from config)
        self.rng = rng                                      # Random generator passed in, so each run can use its own seed
        self.shares = 1/no_of_arms                          # Equal split among arms
        self.visits = np.zeros(no_of_arms, dtype=int)
        self.orders = np.zeros(no_of_arms, dtype=int)
        self.profits = np.zeros(no_of_arms, dtype=float)

    def allocate(self, visitors):
        """
        Allocate visitors equally among the arms using multinomial distribution.
        """

        visits = self.rng.multinomial(                      # Split visitors equally among arms
            n=visitors, 
            pvals=[self.shares]*self.no_of_arms
        )                                                   
        return visits

    def update(self, visits, bought):
        """
        Update the shares based on the number of orders (bought) for each arm recieved.
        Can calculate profits as per the config
        """

        self.visits += visits
        self.orders += bought
        self.profits += bought * self.profit_per_order      # Update profits based on the number of orders and profit per order

    def choice_test(self):
        """
        Statistical test.
        """
        profits = self.profit_per_order
        bonferroni_correction = self.no_of_arms - 1         # Number of comparisons (excluding control)
        welch_results = []
        control = 0

        p_control = self.orders[control] / self.visits[control] if self.visits[control] > 0 else 0
        mean_control = profits[control] * p_control
        var_control = profits[control]**2 * p_control * (1 - p_control)

        for arm in range(1, self.no_of_arms):
            p_arm = self.orders[arm] / self.visits[arm] if self.visits[arm] > 0 else 0
            mean_arm = profits[arm] * p_arm
            var_arm = profits[arm]**2 * p_arm * (1 - p_arm)

            t_statistic = (mean_arm - mean_control) / np.sqrt(var_arm / self.visits[arm] + (var_control / self.visits[control]))
            p_value = 2 * (norm.sf(abs(t_statistic)))       # Two-tailed test
            welch_results.append((arm, t_statistic, p_value, mean_arm))

        winners = []

        for arm, t_statistic, p_value, mean_arm in welch_results:
            if (mean_arm > mean_control) and (p_value < (0.05/bonferroni_correction)):  # Bonferroni correction for multiple comparisons
                winners.append((arm, mean_arm))

        if winners:
            # print(f"Winners: {winners}")
            arm, mean = max(winners, key=lambda x: x[1])                                # Choose the arm with the highest mean profit per visitor
            return arm
        else:
            return 0

    def should_stop(self, hour):
        return False


class PeekingAB(EqualSplit):

    def __init__(self, no_of_arms, profits, rng):
        super().__init__(no_of_arms, profits, rng)
        self.policy_name = "PeekingAB"

    def should_stop(self, hour):
        if (hour%24 == 23) and (self.choice_test() != 0):
            return True
        return False


class BayesianAB(EqualSplit):

    def __init__(self, no_of_arms, profits, rng):
        super().__init__(no_of_arms, profits, rng)
        self.policy_name = "BayesianAB"
        self.threshold = 1e-2
        self.S = 5000
        self.expected_loss = np.array([])
        self.visits_in_prev_loss_update = 0

    def _updating_losses(self):
        """
        protected updating rule
        """
        self.a = 1 + self.orders
        self.b = 1 + (self.visits - self.orders)
        worlds = self.rng.beta(self.a, self.b, size=(self.S, self.no_of_arms)) * self.profit_per_order
        losses = worlds.max(axis=1, keepdims=True) - worlds
        self.expected_loss = losses.mean(axis=0)
        self.visits_in_prev_loss_update = self.visits.sum()

    def choice_test(self):
        """
        winner arm is returned
        """
        if self.visits.sum() != self.visits_in_prev_loss_update:
            self._updating_losses()
        return self.expected_loss.argmin()


    def should_stop(self, hour):
        """
        tells when to stop test as per criteria
        """
        if (hour%24 == 23):
            self._updating_losses()
            E_loss = self.expected_loss.min()
            if E_loss < self.threshold:
                return True
        return False


class ThompsonAB(BayesianAB):

    def __init__(self, no_of_arms, profits, rng):
        super().__init__(no_of_arms, profits, rng)
        self.policy_name = "ThompsonAB"
        self.shares = [1/no_of_arms] * no_of_arms
        self.S = 200                                        # worlds per hour (200 keeps shares accurate to about +-3 points)

    def allocate(self, visitors):
        """
        Allocate visitors among the arms using multinomial distribution.
        """
        
        self.a = 1 + self.orders
        self.b = 1 + self.visits - self.orders

        worlds = self.rng.beta(self.a, self.b, size=(self.S, self.no_of_arms)) * self.profit_per_order

        winners = worlds.argmax(axis=1)
        self.shares = np.bincount(winners, minlength=self.no_of_arms) / self.S
        visits = self.rng.multinomial(
            n=visitors,
            pvals=self.shares
        )

        return visits

    def should_stop(self, hour):
        return False

class BayesianThompsonAB(ThompsonAB):

    def __init__(self, no_of_arms, profits, rng):
        super().__init__(no_of_arms, profits, rng)
        self.policy_name = "BayesianThompson"

    def should_stop(self, hour):
        return BayesianAB.should_stop(self, hour)
        