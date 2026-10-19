from visit_simulator import offer_map, lambda_rate, rng, days
from stats_tests import two_prop_z, welch_ttest
from policies import EqualSplit
import configparser
import numpy as np

# Config parser init
config = configparser.ConfigParser()
config.read("config.ini")

# Reshaping the flat 1440 minutes
lambda_hourly_rate = lambda_rate.reshape(24, 60).sum(axis=1)  # Sum over each hour to get hourly rates

# p_values and profits from offer_map
pvals = [offer_map[arm]['params'][0] for arm in range(4)]
profits = [offer_map[arm]['params'][1] for arm in range(4)]
no_of_arms = config.getint("experiment", "no_of_arms")

if __name__ == "__main__":
    visits_per_arm = np.zeros(4, dtype=int)   
    orders_per_arm = np.zeros(4, dtype=int)
    policy = EqualSplit(no_of_arms, profits, rng)
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

    winner = policy.choice_test()
    print(f"Winner arm: {winner} with offer: {offer_map[winner]['label']}")