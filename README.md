# Real-Time Bayesian Experimentation Engine

> *Every day an offer test runs, some customers are shown the loser, and nobody can tell yet
> which one it is. What if the experiment could learn while it runs?*

A simulator and decision engine for choosing between checkout offers on a quick-commerce app
(Blinkit / Zomato style). It asks one question: **can a Bayesian bandit pick a more profitable
offer, faster and with less wasted traffic, than a standard fixed-length A/B test?**

All data is simulated, so every method can be scored against the known truth.

---

## What it does today

The simulator produces a realistic stream of cart-page visits for four competing offers.

| Capability | How it works |
|---|---|
| **Traffic that follows the clock** | Poisson arrivals whose rate changes through the day: quiet nights, a mid-day plateau, and a big evening peak |
| **Fresh randomness every day** | Each simulated day draws its own visit counts, so days differ the way real days do |
| **Returning customers** | A configurable share of visits comes from users who visited before |
| **Fair, repeatable offer assignment** | A salted SHA-256 hash maps each user to one of four offers, so a returning user always sees the same offer |
| **Order outcomes with a known truth** | Each visit orders with the offer's true probability, and earns the offer's profit if it does |
| **Event log** | Every visit is saved to `outputs/visit_log.csv`: day, minute, user, returning flag, offer, ordered, profit |
| **Everything is configurable** | True rates, profits, daily volume, number of days, seed and returning share live in `config.ini` |

The four offers (toy values chosen so the best offer for conversion is not the best for profit):

| Offer | True order rate | Profit per order | Profit per visitor |
|---|---|---|---|
| 0. No offer (control) | 8% | ₹90 | ₹7.20 |
| 1. Free delivery | 10% | ₹70 | ₹7.00 |
| 2. ₹50 off | 12% | ₹40 | ₹4.80 |
| 3. ₹20 off above ₹299 | 11% | ₹70 | **₹7.70** |

---

## Assumptions

Everything here is chosen by hand unless a source is named.

| Area | Assumption |
|---|---|
| **Data** | Fully synthetic. No Eternal, Blinkit or Zomato data is used |
| **Traffic volume** | About 20,000 cart-page visits a day |
| **Daily shape** | Share of the day's traffic: 07–11 → 16%, 11–17 → 24%, 17–23 → 46%, 23–02 → 10%, 02–07 → 4% (floor). The windows follow the ranges in an industry article (see Sources), which cites no dataset or method, so treat them as plausible ranges, not measured truth. The 02–07 floor is my own choice |
| **Arrivals** | Visits are independent, with a rate that is flat within each window |
| **Returning visits** | 15% of visits come from a user who already visited in the campaign window. This is an assumption, not a sourced figure |
| **Orders** | Each visit is an independent coin flip with the offer's true rate |
| **Profit** | Fixed per order for each offer (margin minus discount cost) |
| **Stability** | True rates do not change over time (no weekday, hour or novelty effects) |
| **Demand** | Orders equal demand. No stock-outs are modelled |

---

## Metrics and numbers

Measured on the current code: 3 simulated days, seed 42, 60,374 visits.

**Does the simulator behave as designed?**

| Check | Target | Result |
|---|---|---|
| Visits per day | about 20,000, varying day to day | 20,320 / 19,884 / 20,170 |
| Share of visits in each time window | 4 / 16 / 24 / 46 / 10 % | 4.0 / 16.1 / 24.0 / 46.0 / 9.9 % |
| Returning share | 15% | 15.1% |
| Visitors per offer | about 15,100 each | 15,227 / 15,076 / 15,012 / 15,059 |
| Users shown more than one offer | 0 | 0 |
| Two experiments assigned independently (100,000 users, 16 combinations, expected 6,250 each) | even spread | 6,100 – 6,429, whereas plain `user_id % 4` fills only 4 of the 16 combinations |

**Does it recover the truth?**

| Offer | True order rate | Observed (± standard error) | True profit per visitor | Observed |
|---|---|---|---|---|
| 0 | 8.0% | 8.43% ± 0.23 | ₹7.20 | ₹7.59 |
| 1 | 10.0% | 9.92% ± 0.24 | ₹7.00 | ₹6.95 |
| 2 | 12.0% | 11.66% ± 0.26 | ₹4.80 | ₹4.67 |
| 3 | 11.0% | 10.80% ± 0.25 | ₹7.70 | ₹7.56 |

**What a standard A/B test makes of this data (single run, 50/50 split, 3 days):**

| Question | Result |
|---|---|
| Is offer 2 better than control on **conversion**? | Yes, very clearly (z = 9.35) |
| Is offer 3, the true profit winner, better than control on **profit per visitor**? | **No.** Observed gap −₹0.03 against a true gap of +₹0.50 (standard error ₹0.27, z = −0.1) |
| Visitors per offer needed to detect a ₹0.50 profit gap (80% power, 5% level) | about **34,000**, calculated from the toy parameters. Three days gave about 15,000 |

---

## Why it matters: one festive week, one wrong click

Imagine a retailer with a festive campaign that lasts a week. It has four candidate checkout
offers and 20,000 cart visits a day. The usual plan is to split traffic evenly, wait, and
pick the winner.

After three days, the dashboard says offer 2 (₹50 off) has the highest order rate, and the
result is overwhelming (z = 9.35). A team that watches conversion rolls it out. But in this
simulation offer 2 earns **₹4.80 per visitor against ₹7.70 for the best offer**. At 20,000
visits a day, that is about **₹58,000 lost every day** the wrong offer runs. The profit
numbers that would have exposed it are still too noisy: the true best offer looks no better
than doing nothing.

Real systems run into the same pattern:

- **JD.com** built an advertising experiment system on bandits instead of fixed-sample tests.
  Its authors report about 27% more clicks during testing.
- **Optimizely** rebuilt its statistics engine around "always valid" inference because
  customers kept checking results mid-test, which inflates false positives.
- **Netflix** chooses artwork with contextual bandits instead of waiting for slow cycles of
  A/B tests.
- **Spotify** compared sequential testing methods in simulation to choose one that suits how
  its data arrives.

**What the finished engine is built to show:**

- **The price of peeking, measured.** How often a daily-checked fixed test declares a winner
  when all four offers are identical.
- **Profit-aware decisions.** Picking offer 3 over offer 2 by weighing order probability
  against profit per order, not conversion alone.
- **Less money wasted while learning.** Total profit lost compared with always showing the
  best offer, for a fixed split versus a Bayesian bandit (Thompson sampling).
- **Faster correct decisions on short campaigns.** Days until each method commits to the
  right offer, in a 3-day and a 14-day campaign.
- **Honest limits.** Scenarios where the plain A/B test is just as good or better, such as a
  tiny real difference or a need for an unbiased effect size.
- **A live decision service.** A Beta posterior per offer held in Redis, with endpoints that
  assign an offer and record an outcome.

These are the goals of the finished system, not results yet measured.

---

## Run it

The scripts read `config.ini` from the current directory, so run from inside `Simulations/`.

```text
cd Simulations
python visit_simulator.py   # one realistic run, visit by visit
python monte_carlo.py       # 500 campaigns of one policy and scenario
```

These write `outputs/visit_log.csv` and `outputs/monte_carlo/summary_*.csv` / `daily_regret_*.csv`. Dependencies: `numpy`, `pandas`, `matplotlib`. Python 3.13 was used.

`config.ini` keys:

| Section | Keys |
|---|---|
| `[rates]` | `arm_1` … `arm_4`: true order rate per offer |
| `[profits]` | `arm_1` … `arm_4`: profit per order after discount |
| `[experiment]` | `id` (hash salt), `seed`, `days`, `visitors_per_day`, `returning_visit_share`, `total_distinct_users` |

---

## Sources

- Daypart shares: Swapnil Gupta, Zane, *Quick-commerce daypart ad pacing and hourly budgets*
  (2 Aug 2026), <https://zane.marketing/quick-commerce-daypart-ad-pacing-hourly-budgets/>
- Geng et al., *Comparison Lift: Bandit-based Experimentation System for Online Advertising*
  (JD.com), <https://arxiv.org/abs/2009.07899>
- Johari, Pekelis and Walsh, *Always Valid Inference* (Optimizely), <https://arxiv.org/abs/1512.04922>
- Netflix artwork personalization (summary),
  <https://www.reforge.com/blog/brief-netflix-artwork-personalization-through-multi-armed-bandit-testing>
- Spotify, *Choosing a Sequential Testing Framework*,
  <https://engineering.atspotify.com/2023/3/choosing-sequential-testing-framework-comparisons-and-discussions>
- Evan Miller, *How Not To Run an A/B Test*, <https://www.evanmiller.org/how-not-to-run-an-ab-test.html>
- Chris Stucchio, *Bayesian A/B Testing at VWO*, <https://www.chrisstucchio.com/pubs/VWO_SmartStats_technical_whitepaper.pdf>
- Russo et al., *A Tutorial on Thompson Sampling*, <https://arxiv.org/abs/1707.02038>
