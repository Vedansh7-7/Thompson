from users import offer_map, lambda_rate, rng, days
import configparser
import numpy as np

# Config parser init
config = configparser.ConfigParser()
config.read("config.ini")

# Reshaping the flat 1440 minutes
lambda_hourly_rate = lambda_rate.reshape(24, 60)

# Shared configuration for the light simulation
shares = []
shares.append([config.getfloat("traffic_shares", f"arm_{i+1}") for i in range(4)])

# p_values and profits from offer_map
pvals = [offer_map[arm]['params'][0] for arm in range(4)]
profits = [offer_map[arm]['params'][1] for arm in range(4)]

# Defining class for the light simulation
class LightSimulation:
    ...



if __name__ == "__main__":
    print("Simulating light version of the experiment...")
    poisson_visitors = rng.poisson(lambda_hourly_rate)
    arm_id = rng.multinomial(n=poisson_visitors[0], pvals=shares)
    print(arm_id, poisson_visitors[0])
            # bought = bool(rng.binomial(n=poisson_visitors[h], p=pvals[arm_id]))

            # if bought:
            #     profit = profits[arm_id]
            # else:
            #     profit = 0.0

            # d = {
            #     "day": day,
            #     "hour": h,
            #     "arm_id": arm_id,
            #     "bought": bought,
            #     "profit": profit
            # }
            # data.append(d)
    
    print("Simulation complete. Saving to light_sim.csv...")