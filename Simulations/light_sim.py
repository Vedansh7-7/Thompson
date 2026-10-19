from users import offer_map, lambda_rate, rng, days
import configparser
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

# Defining class for the light simulation
class LightSimulation:
    ...



if __name__ == "__main__":
    data = []
    total_visitors = 0
    orders = 0
    print("Simulating light version of the experiment...")
    for day in range(days):
        poisson_visitors = rng.poisson(lambda_hourly_rate)
        for h in range(24):
            visitors = rng.multinomial(n=poisson_visitors[h], pvals=shares)
            total_visitors += sum(visitors)
            bought = rng.binomial(n=visitors, p=pvals)
            orders += sum(bought)
            profit = bought * profits

            data_per_hour = {
                "day": day,
                "hour": h,
                "visitors": visitors.sum(),
                "bought": bought.sum(),
                "profit": profit.sum()
            }
            data.append(data_per_hour)
    print("Simulation complete. Summary:", total_visitors, "total visitors over", days, "days.\nTotal orders:", orders, "with total profit:", sum(d['profit'] for d in data), "orders/visitors ratio:", orders/total_visitors)

