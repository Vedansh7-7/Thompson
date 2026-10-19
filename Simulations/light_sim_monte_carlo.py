from users import offer_map, lambda_rate, rng, days, scenerio
from class_lib import EqualSplit, PeekingAB, BayesianAB
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

# stopped = False
# day_stopped = None
# daily_regret = []

def run_campaign(Policy, days, rng):
    stopped = False
    day_stopped = None
    daily_regret = []
    policy = Policy(no_of_arms, profits, rng)
    regret = 0
    
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
                day_stopped = day+1
                break

        
        daily_regret.append(regret.sum())

    choosen_arm = policy.choice_test()

    return choosen_arm, regret, policy.policy_name, stopped, day_stopped, daily_regret

if __name__ == "__main__":
    data = []
    cummulative = []                                    # one row per campaign: regret at the end of each day
    number_of_campaigns = config.getint("experiment", "number_of_campaigns")
    policy = BayesianAB
    master = np.random.SeedSequence(config.getint("experiment", "seed"))
    children = master.spawn(number_of_campaigns)

    for run_index, child in enumerate(children):
        rng = np.random.default_rng(child)
        winner, regret, policy_name, stopped, day_stopped, daily_regret = run_campaign(policy, days, rng)
        correct = bool(true_profit_values[winner] == true_profit_values.max())
        run = {
            "index": run_index,
            "policy": policy_name,
            "scenario": scenerio,
            "days": days,
            "winner": winner,
            "correct": correct,
            "regret": round(sum(regret), 2),
            "stopped": stopped,
            "stop_day": day_stopped
        }
        regret_run = {"index": run_index}
        for i, r in enumerate(daily_regret):
            regret_run[f"regret_d{i+1}"] = round(r, 2)
        data.append(run)
        cummulative.append(regret_run)

    df = pd.DataFrame(data)
    df.to_csv(f'../outputs/MonteCarlo/MC_output_{policy_name}_{scenerio}_{days}d.csv', index=False)
    print(f"Saved as '../outputs/MonteCarlo/MC_output_{policy_name}_{scenerio}_{days}d.csv'")
    print("Average regret =", df['regret'].mean())

    df_cum = pd.DataFrame(cummulative)
    df_cum.to_csv(f'../outputs/MonteCarlo/cummulative_regret_{policy_name}_{scenerio}_{days}d.csv', index=False)
    print(f"Saved as '../outputs/MonteCarlo/cummulative_regret_{policy_name}_{scenerio}_{days}d.csv'")