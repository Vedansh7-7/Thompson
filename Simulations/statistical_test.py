import numpy as np
from scipy.stats import norm, ttest_ind


def two_prop_z(x1, n1, x2, n2):
    """Two-proportion z-test (two-sided).

    x1, n1: orders and visitors in the first group (e.g. control)
    x2, n2: orders and visitors in the second group (e.g. a treatment)

    Returns (z, p_value). z is positive when group 2 has the higher rate.
    """
    if not (0 <= x1 <= n1 and 0 <= x2 <= n2 and n1 > 0 and n2 > 0):
        raise ValueError("need 0 <= x <= n and n > 0 for both groups")

    p1 = x1 / n1
    p2 = x2 / n2

    # pooled rate: under the null both groups share one true rate,
    # so it is estimated from the two groups in the test only
    p_bar = (x1 + x2) / (n1 + n2)
    if p_bar in (0, 1):
        raise ValueError("pooled rate is 0 or 1, the standard error would be zero")

    std_err = np.sqrt(p_bar * (1 - p_bar) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / std_err
    p_value = 2 * norm.sf(abs(z))
    return z, p_value

def welch_ttest(x1, x2):
    """Welch's t-test for two independent samples with unequal variances.

    x1, x2: arrays of observations in the two groups

    Returns (t_statistic, p_value). t_statistic is positive when group 2 has the higher mean.
    """
    t_statistic, p_value = ttest_ind(x1, x2, equal_var=False)
    return t_statistic, p_value


if __name__ == "__main__":
    # # worked example from the lesson: 80/1000 vs 100/1000 -> z about 1.56, p about 0.12
    # print(two_prop_z(80, 1000, 100, 1000))
    # # same rates with 5x the visitors -> z about 3.5
    # print(two_prop_z(400, 5000, 500, 5000))

    ...
