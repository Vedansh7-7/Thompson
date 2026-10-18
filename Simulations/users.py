# IMPORTS
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import hashlib
import configparser

# DEFINITONS
config = configparser.ConfigParser()
config.read("config.ini")

# PARAMETERS
seed = config.getint("experiment", "seed")
rng = np.random.default_rng(seed)
days = config.getint("experiment", "days")
return_rate = config.getfloat("experiment", "returning_visit_share")
total_visitors_per_day = config.getint("experiment", "visitors_per_day")
total_distinct_users = max(config.getint("experiment", "total_distinct_users"), (total_visitors_per_day*days))

schedule = [
    (120, 420, 0.04),
    (420, 660, 0.16),
    (660, 1020, 0.24),
    (1020, 1380, 0.46),
    (1380, 1560, 0.1)
]

lambda_rate = np.zeros(1440)

for start, end, pct in schedule:
    window_size = end-start
    lam_rate = (pct*total_visitors_per_day)/window_size
    for i in range(start, end):
        lambda_rate[i%1440] = lam_rate


print("Validating cutomers dsitribution:", lambda_rate.sum(), "=", total_visitors_per_day)  # testing

# fig, ax = plt.subplots(ncols=2)  # testing
# ax[0].plot(lambda_rate)  # testing
# ax[1].plot(poisson_visitors)  # testing
# plt.show()  # testing 

not_visited_user_ids = np.arange(1, total_distinct_users+1)
rng.shuffle(not_visited_user_ids)
next_user_idx = 0
visited_user_ids = np.array([], dtype=int)

offer_map = {
    0: {"label": "Control",
        "params": [config.getfloat("rates", "arm_1"), config.getfloat("profits", "arm_1")]},
    1: {"label": "FreeDelivery",
        "params": [config.getfloat("rates", "arm_2"), config.getfloat("profits", "arm_2")]},
    2: {"label": "INR_50_off",
        "params": [config.getfloat("rates", "arm_3"), config.getfloat("profits", "arm_3")]},
    3: {"label": "INR_20_off_above_299",
        "params": [config.getfloat("rates", "arm_4"), config.getfloat("profits", "arm_4")]}
}

# FUNCTIONS
def assign_arm(user_id):
    test_key = str(user_id) + ":" + config["experiment"]["id"]
    byte_key = test_key.encode('UTF-8')
    hashed_hex = hashlib.sha256(byte_key)   # Into hex string
    hashed_str = hashed_hex.hexdigest()
    hex_str = int(hashed_str, 16)
    arm_id = hex_str%4
    return arm_id


def simulate_visit(arm):
    p, profit = offer_map[arm]['params']
    bought = bool(rng.binomial(n=1, p=p))
    if not bought:
        profit = 0.0
    return (bought, profit)

def pick_user():
    global next_user_idx, visited_user_ids

    choose = rng.binomial(n=1, p=return_rate)
    if choose and len(visited_user_ids) > 0:
        uid = rng.choice(visited_user_ids)
        visited = 1
    else:
        uid = not_visited_user_ids[next_user_idx]
        next_user_idx += 1
        visited_user_ids = np.append(visited_user_ids, uid)
        visited = 0

    return (uid, visited)

if __name__ == "__main__":
    data = [
        # "day": [],
        # "time_min": [],
        # "user_id": [],
        # "is_returning": [],
        # "arm_id": [],
        # "bought": [],
        # "profit": []
    ]

    for day in range(days):
        poisson_visitors = rng.poisson(lambda_rate)
        for t_min in range(1440):
            for i in range(poisson_visitors[t_min]):
                uid, visited = pick_user()
                arm_id = assign_arm(uid)
                bought, profit = simulate_visit(arm_id)
                user_info = {
                    "day": day,
                    "time_min": t_min,
                    "user_id": uid,
                    "is_returning": visited,
                    "arm_id": arm_id,
                    "bought": bought,
                    "profit": profit
                }
                data.append(user_info)
    df = pd.DataFrame(data)
    df.to_csv('output.csv', index=False)