from users import offer_map, lambda_rate, rng, days
from statistical_test import two_prop_z, welch_ttest
import configparser
import scipy.stats as norm
import numpy as np

# Config parser init
config = configparser.ConfigParser()
config.read("config.ini")

# Reshaping the flat 1440 minutes
lambda_hourly_rate = lambda_rate.reshape(24, 60).sum(axis=1)  # Sum over each hour to get hourly rates

# Shared configuration for the light simulation
shares = [config.getfloat("traffic_shares", f"arm_{i+1}") for i in range(4)]

# p_values and profits from offer_map
pvals = [offer_map[arm]['params'][0] for arm in range(4)]
profits = [offer_map[arm]['params'][1] for arm in range(4)]
no_of_arms = config.getint("experiment", "no_of_arms")

# Defining class for the light simulation
class EqualSplit:
    def __init__(self):
        self.policy_name = "EqualSplit"
        self.shares = 1/no_of_arms  # Equal split among arms
        self.visits = np.zeros(no_of_arms, dtype=int)
        self.orders = np.zeros(no_of_arms, dtype=int)
        self.profits = np.zeros(no_of_arms, dtype=float)

    def allocate(self, visitors):
        """
        Allocate visitors equally among the arms using multinomial distribution.
        """

        visits = rng.multinomial(n=visitors, pvals=[self.shares]*no_of_arms)  # Split visitors equally among arms
        return visits

    def update(self, visits, bought):
        """
        Update the shares based on the number of orders (bought) for each arm recieved.
        Can calculate profits as per the config
        """

        self.visits += visits
        self.orders += bought
        self.profits += bought * np.array(profits)  # Update profits based on the number of orders and profit per order
        pass

    def choice_test(self):
        """
        Statistical test to check if the observed order rates are significantly different from the expected rates.
        """
        bonferroni_correction = no_of_arms - 1  # Number of comparisons (excluding control)
        welch_results = []
        control = 0
        p_control = self.orders[control] / self.visits[control] if self.visits[control] > 0 else 0
        mean_control = profits[control] * p_control
        var_control = mean_control**2 * p_control * (1 - p_control)
        for arm in range(1, no_of_arms):
            p_arm = self.orders[arm] / self.visits[arm] if self.visits[arm] > 0 else 0
            mean_arm = profits[arm] * p_arm
            var_arm = mean_arm**2 * p_arm * (1 - p_arm)

            t_statistic = (mean_arm - mean_control) / np.sqrt(var_arm / self.visits[arm] + (var_control / self.visits[control]))
            p_value = 2 * (1 - norm.cdf(abs(t_statistic)))  # Two-tailed test
            welch_results.append((arm, t_statistic, p_value, mean_arm))
        winners = np.array([], dtype=tuple)
        for arm, t_statistic, p_value, mean_arm in welch_results:
            if (mean_arm > mean_control) and (p_value < (0.05/bonferroni_correction)):  # Bonferroni correction for multiple comparisons
                print(f"Arm {arm} is significantly better than control with t-statistic: {t_statistic:.4f}, p-value: {p_value:.4f}, mean profit per visitor: {mean_arm:.4f}")
                winners.append((arm, mean_arm))
        if winners:
            print(f"Winners: {winners}")
            arm, mean = winners.argmax(axis=1)
            return arm
        else:
            print("No arm is significantly better than control.")
            return 0


if __name__ == "__main__":
    visits_per_arm = np.zeros(4, dtype=int)   
    orders_per_arm = np.zeros(4, dtype=int)
    policy = EqualSplit()
    print(f"Simulating light version of the experiment for policy, {policy.policy_name}...")
    for day in range(days):
        visits_per_hour = rng.poisson(lambda_hourly_rate)      # 24 counts, refreshes each day (simulated)
        for h in range(24):
            visitors = policy.allocate(visits_per_hour[h])     # split the hour across arms (policy)
            bought = rng.binomial(n=visitors, p=pvals)         # orders per arm (simulated)
            policy.update(visitors, bought)                    # update the the results (policy)
            

    # SUMMARY AND TABLE __ --- ___ ___---- ___ ___ 
      
    visits_per_arm = policy.visits                                       
    orders_per_arm = policy.orders       
    total_visitors = visits_per_arm.sum()
    print("Simulation complete.\nSummary:")
    # ---------- per-arm table and validation ----------
    true_rates = np.array(pvals)
    true_value = true_rates * np.array(profits)              # true profit per visitor
    obs_rates = orders_per_arm / visits_per_arm
    obs_value = orders_per_arm * np.array(profits) / visits_per_arm
    # a check passes if the observed rate is within 3 standard errors of the truth
    std_err = np.sqrt(true_rates * (1 - true_rates) / visits_per_arm)
    rate_ok = np.abs(obs_rates - true_rates) < 3 * std_err

    print(f"\n{'arm':<4}{'offer':<23}{'visits':>8}{'orders':>8}{'rate':>9}{'true':>7}"
          f"{'profit/visitor':>16}{'true':>7}  check")
    for arm in range(4):
        print(f"{arm:<4}{offer_map[arm]['label']:<23}{visits_per_arm[arm]:>8,}{orders_per_arm[arm]:>8,}"
              f"{obs_rates[arm]:>9.4f}{true_rates[arm]:>7.2f}"
              f"{obs_value[arm]:>16.2f}{true_value[arm]:>7.2f}  {'OK' if rate_ok[arm] else 'CHECK'}")

    expected_visits = days * lambda_hourly_rate.sum()
    visits_ok = abs(total_visitors - expected_visits) < 3 * np.sqrt(expected_visits)
    print(f"{'total':<27}{total_visitors:>8,}   expected about {expected_visits:,.0f}"
          f"  {'OK' if visits_ok else 'CHECK'}")
    print("All checks passed." if rate_ok.all() and visits_ok else "Some checks failed: look at the CHECK rows.")

