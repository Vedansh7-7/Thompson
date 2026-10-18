# Real-Time Bayesian Experimentation Engine

A simulator and decision engine for choosing between checkout offers on a quick-commerce app
(Blinkit / Zomato-style). The question: **can a Bayesian bandit make better offer decisions,
faster and with less wasted traffic, than a standard fixed-length A/B test?**

> **Status: work in progress (target: Oct 25, 2026).** The traffic simulator is partly built.
> The engine, API and dashboard are not started. See [Roadmap](#roadmap).

> **All data in this project is simulated.** No real Eternal, Blinkit or Zomato data is used.
> Every number below is an assumption unless it is marked as measured.

---

## 1. The problem

A quick-commerce app wants to decide which offer to show on the cart page during a campaign,
for example free delivery or a flat discount.

The usual approach is a fixed A/B test: split traffic evenly, wait about two weeks, run a
significance test, pick a winner. Three weaknesses:

- **Wasted traffic.** Losing offers keep being shown for the whole test.
- **Peeking.** Checking results daily and stopping at the first p < 0.05 raises the
  false-positive rate above the nominal 5%.
- **Short campaigns.** A festive campaign can end before a two-week test does.

**This project's approach:** keep a live Beta posterior of the order rate for each offer, shift
traffic toward offers that are probably better (Thompson sampling), stop when the expected cost
of a wrong choice is small, and optimise **profit per visitor**, not just conversion.

Because the data is simulated with known true rates, every method can be scored against the
truth: total profit (regret), wrong-winner rate, false-alarm rate on A/A tests, and time to a
correct decision.

---

## 2. The experiment (toy parameters)

Unit: one cart-page visit. Outcome: whether the visitor ordered, and the profit if they did.

| Arm | Offer | True order rate | Profit per order after discount | Profit per visitor |
|---|---|---|---|---|
| 0 | No offer (control) | 8% | ₹90 | ₹7.20 |
| 1 | Free delivery (costs ₹20) | 10% | ₹70 | ₹7.00 |
| 2 | ₹50 off | 12% | ₹40 | ₹4.80 |
| 3 | ₹20 off above ₹299 | 11% | ₹70 | **₹7.70** |

These values are **chosen by hand** to make a point: arm 2 has the highest conversion but the
lowest profit, and arm 3 is the true profit winner. A team that watches only conversion picks
the wrong offer.

The true rates live only inside the simulator. The engine sees events, never the truth. A
separate scoring step compares the engine's decisions with the truth afterward.

---

## 3. Simulator design

Two independent layers, plus a rule for who the visitors are.

| Layer | Question | Model |
|---|---|---|
| Arrivals | How many visits happen this minute? | Poisson(λ_t), where λ_t depends on the time of day |
| Conversion | Does this visitor order? | Bernoulli(p), where p is the assigned arm's true rate |
| Visitors | Who is visiting? | New users get the next ID. About 15% of visits are returning users, chosen from past visits (so frequent visitors return more often) |

### Arm assignment

Assignment is deterministic and sticky: the same user always gets the same arm. It uses a
salted SHA-256 hash of `"<user_id>:<experiment_id>"`, taken modulo the number of arms.

Why hashing instead of `user_id % 4`: with plain modulo, two experiments running together
get identical splits, so their effects cannot be separated. Salting with the experiment ID
makes the splits independent.

### Time-of-day traffic

The daily traffic shape follows daypart windows taken from an industry article (see
[Sources](#sources-and-caveats)):

| Window | Share of daily orders (source range) |
|---|---|
| 07:00 – 11:00 | 15 – 20% |
| 11:00 – 17:00 | 20 – 25% |
| 17:00 – 23:00 | 40 – 48% |
| 23:00 – 02:00 | 8 – 12% |
| 02:00 – 07:00 | not given in the source |

Choices made for this project (shares sum to 100%):

| Window | Share used |
|---|---|
| 07:00 – 11:00 | 16% |
| 11:00 – 17:00 | 24% |
| 17:00 – 23:00 | 46% |
| 23:00 – 02:00 | 10% |
| 02:00 – 07:00 | 4% (floor, assumption) |

- λ per minute for a window = share × daily total ÷ minutes in the window.
- The 02:00 – 07:00 floor is my assumption, since the source gives no figure and a
  completely silent app is unrealistic.
- Target volume of about 20,000 visits a day. *(Assumption.)*
- The rate is flat inside each window, so it jumps at window edges. Smoothing is a possible
  later improvement.

---

## 4. Verified so far

Measured with seed 42 on the current code (`Simulations/users.py`):

| Check | Result |
|---|---|
| Arm split over 100,000 user IDs (expected 25,000 each, spread about ±137) | 25,013 / 24,991 / 25,087 / 24,909 |
| Independence of two experiments (16 combinations, expected 6,250 each, spread about ±77) | Range 6,100 – 6,429 |
| Same test with plain `user_id % 4` | Only 4 of 16 combinations used, 25,000 each; the other 12 empty |
| Observed order rate over 25,000 visits per arm (true 0.08 / 0.10 / 0.12 / 0.11) | 0.0799 / 0.1005 / 0.1202 / 0.1118 |

Not yet measured: the Poisson arrival layer, the A/B baseline, the bandit, and any comparison
between them.

---

## 5. Repository layout

```text
Simulations/
├── config.ini    # true order rates, profits per order, experiment id, days, seed, visitors per day
└── users.py      # daily rate table, arm assignment (hashing), visit outcome (Bernoulli draw)
```

`config.ini` keys:

| Section | Keys |
|---|---|
| `[rates]` | `arm_1` … `arm_4`: true order rate per arm |
| `[profits]` | `arm_1` … `arm_4`: profit per order after discount |
| `[experiment]` | `id` (hash salt), `days`, `seed`, `visitors_per_day` |

---

## 6. Running it

The scripts read `config.ini` from the current directory, so run them from inside `Simulations/`.

```text
cd Simulations
python users.py
```

Running `users.py` assigns 100,000 users to arms and prints the share of each arm, then shows
a histogram. Dependencies: `numpy`, `pandas`, `matplotlib`. Python 3.13 was used.

---

## 7. Roadmap

- [x] Deterministic arm assignment (hashing), checked for even split and independence
- [x] Bernoulli visit outcomes, checked against the true rates
- [ ] Daily traffic schedule and Poisson arrivals
- [ ] Returning users with sticky arms
- [ ] Fixed-horizon A/B test baseline (two-proportion z-test) and sample-size calculation
- [ ] Peeking simulation: false-positive rate under daily checks
- [ ] Bayesian A/B with expected-loss stopping
- [ ] Thompson sampling bandit and regret curves
- [ ] Profit-aware reward (P(order) × expected profit per order)
- [ ] Scenarios: clear winner, tiny effect, A/A, short vs long campaign
- [ ] Redis state, FastAPI endpoints, Docker Compose, dashboard
- [ ] Final write-up with measured results only

---

## 8. Limitations

- All data is synthetic. Findings describe the simulator, not any real business.
- The toy rates, profits and daily volume are assumptions.
- Poisson arrivals assume visits are independent. Real traffic is burstier (push notifications,
  campaigns), so real arrivals vary more than Poisson allows.
- Conversion rates are fixed over time. Real rates change by weekday, hour and novelty.
- Sales are treated as demand. No stock-outs are modelled.

---

## Sources and caveats

- Daypart order shares: Swapnil Gupta, Zane, *Quick-commerce daypart ad pacing and hourly
  budgets*, published 2 Aug 2026, <https://zane.marketing/quick-commerce-daypart-ad-pacing-hourly-budgets/>.
  The article presents these shares as approximate observations from metro dark stores and
  cites no dataset, sample size or method. Treat them as **unverified, plausible ranges**,
  not measured ground truth. The article also notes late-night share is higher in some cities;
  this project uses the national range.
- Methods background: Evan Miller, *How Not To Run an A/B Test* (peeking); Chris Stucchio,
  *Bayesian A/B Testing at VWO* (expected loss); Russo et al., *A Tutorial on Thompson
  Sampling*; Stitch Fix, *Multi-Armed Bandits and the Experimentation Platform*.
