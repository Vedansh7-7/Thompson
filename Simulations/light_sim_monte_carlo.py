from users import offer_map, lambda_rate, rng, days, scenerio
from class_lib import EqualSplit, PeekingAB
import configparser
import numpy as np
import pandas as pd

# Config parser init
config = configparser.ConfigParser()
config.read("config.ini")

# Reshaping the flat 1440 minutes
lambda_hourly_rate = lambda_rate.reshape(24, 60).sum(axis=1)                 # Sum over each hour to get hourly rates

# p and profits from offer_map
probabilities = np.array([offer_map[arm]['params'][0] for arm in range(4)])
profits = np.array([offer_map[arm]['params'][1] for arm in range(4)])

# True profit values = probability * profit
true_profit_values = probabilities * profits
no_of_arms = config.getint("experiment", "no_of_arms")
best_true_profit = true_profit_values.max()

def run_campaign(Policy, days, rng):
    policy = Policy(no_of_arms, profits, rng)
    regret = 0
    stopped = False
    
    for day in range(days):
        visits_per_hour = rng.poisson(lambda_hourly_rate)                   # 24 counts, refreshes each day (simulated)
        for h in range(24):
            if stopped:
                tmp = np.zeros(no_of_arms)
                tmp[chosen] = visits_per_hour[h]
                regret += tmp * (best_true_profit - true_profit_values)
                continue
            visitors = policy.allocate(visits_per_hour[h])                  # split the hour across arms (policy)
            bought = rng.binomial(n=visitors, p=probabilities)              # orders per arm (simulated)
            policy.update(visitors, bought)                                 # update the the results (policy)
            regret += visitors * (best_true_profit - true_profit_values)
            hours = (day * 24 + h)
            if policy.should_stop(hours):
                stopped = True
                chosen = policy.choice_test()
                break

    choosen_arm = policy.choice_test()
    return choosen_arm, regret, policy.policy_name

if __name__ == "__main__":
    data = []
    number_of_campaigns = config.getint("experiment", "number_of_campaigns")
    master = np.random.SeedSequence(config.getint("experiment", "seed"))
    children = master.spawn(number_of_campaigns)

    for run_index, child in enumerate(children):
        rng = np.random.default_rng(child)
        winner, regret, policy_name = run_campaign(PeekingAB, days, rng)
        run = {
            "index": run_index,
            "winner": winner,
            "regret": round(sum(regret), 2)
        }
        data.append(run)

    df = pd.DataFrame(data)
    df.to_csv(f'../outputs/MonteCarlo/MC_output_{policy_name}_{scenerio}_{days}d.csv', index=False)
    print(f"Saved as '../outputs/MonteCarlo/MC_output_{policy_name}_{scenerio}_{days}d.csv'")
    print("Average regret =", df['regret'].mean())