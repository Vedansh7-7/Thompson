from users import offer_map, lambda_rate, rng, days
from class_lib import EqualSplit
import configparser
import numpy as np
import pandas as pd

# Config parser init
config = configparser.ConfigParser()
config.read("config.ini")

# Reshaping the flat 1440 minutes
lambda_hourly_rate = lambda_rate.reshape(24, 60).sum(axis=1)  # Sum over each hour to get hourly rates

# p_values and profits from offer_map
pvals = [offer_map[arm]['params'][0] for arm in range(4)]
profits = [offer_map[arm]['params'][1] for arm in range(4)]
no_of_arms = config.getint("experiment", "no_of_arms")

def run_campaign(policy, days, rng):
    policy = policy(no_of_arms, profits, rng)
    # print(f"Simulating light version of the experiment for policy, {policy.policy_name}...")
    for _ in range(days):
        visits_per_hour = rng.poisson(lambda_hourly_rate)      # 24 counts, refreshes each day (simulated)
        for h in range(24):
            visitors = policy.allocate(visits_per_hour[h])     # split the hour across arms (policy)
            bought = rng.binomial(n=visitors, p=pvals)         # orders per arm (simulated)
            policy.update(visitors, bought)                    # update the the results (policy)
    choosen_arm = policy.choice_test()
    return choosen_arm

if __name__ == "__main__":
    data = []
    number_of_campaigns = config.getint("experiment", "number_of_campaigns")
    master = np.random.SeedSequence(config.getint("experiment", "seed"))
    children = master.spawn(number_of_campaigns)

    for run_index, child in enumerate(children):
        rng = np.random.default_rng(child)
        winner= run_campaign(EqualSplit, days, rng)
        run = {
            "index": run_index,
            "winner": winner
        }
        data.append(run)

    df = pd.DataFrame(data)
    df.to_csv('MC_output.csv', index=False)