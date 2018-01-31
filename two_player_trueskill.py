import math

# Initial mean
MU = 25.

# Initial standard deviation
SIGMA = MU / 3.

# Distance corresponding to ~76% chance of winning
BETA = SIGMA / 2.

# Dynamics factor
TAU = SIGMA / 100.

TAU_SQUARED = TAU * TAU

class Rating:
    def __init__(self, mu=MU, sigma=SIGMA):
        self.mu = mu
        self.sigma = sigma

    def expose(self):
        """Return a conservative estimate of the rating useful for ranking."""
        return self.mu - (MU / SIGMA) * self.sigma

class TwoPlayerTrueSkill:
    """"Specialized implementation of TrueSkill for two-player games with zero
    draw probability.

    Derived from
    https://github.com/moserware/Skills/blob/master/Skills/TrueSkill/TwoPlayerTrueSkillCalculator.cs."""

    def __init__(self, players):
        self.ratings = dict([(p, Rating()) for p in players])

    def update(self, winner, loser):
        a = self.ratings[winner]
        b = self.ratings[loser]

        a_sigma_squared = square(a.sigma)
        b_sigma_squared = square(b.sigma)

        c = math.sqrt(a_sigma_squared + b_sigma_squared + 2. * square(BETA))
        c_squared = square(c)

        diff = (a.mu - b.mu) / c
        denom = cdf(diff)
        v = pdf(diff) / denom if denom else -diff
        w = v * (v + diff)
        assert(0 < w < 1)

        a_mean_multiplier = (a_sigma_squared + TAU_SQUARED) / c
        b_mean_multiplier = (b_sigma_squared + TAU_SQUARED) / c

        a_variance_with_dynamics = a_sigma_squared + TAU_SQUARED
        a_std_dev_multiplier = a_variance_with_dynamics / c_squared

        b_variance_with_dynamics = b_sigma_squared + TAU_SQUARED
        b_std_dev_multiplier = b_variance_with_dynamics / c_squared

        a_new_mu = a.mu + a_mean_multiplier * v
        a_new_sigma = math.sqrt(a_variance_with_dynamics * (1. - w * a_std_dev_multiplier))

        b_new_mu = b.mu - b_mean_multiplier * v
        b_new_sigma = math.sqrt(b_variance_with_dynamics * (1. - w * b_std_dev_multiplier))

        self.ratings[winner].mu = a_new_mu
        self.ratings[winner].sigma = a_new_sigma

        self.ratings[loser].mu = b_new_mu
        self.ratings[loser].sigma = b_new_sigma

    def get_ratings(self):
        return {p: r.expose() for p, r in self.ratings.iteritems()}

def square(x): return x * x

# From https://github.com/sublee/trueskill/blob/master/trueskill/backends.py
def erfc(x):
    """Complementary error function (via `http://bit.ly/zOLqbc`_)"""
    z = abs(x)
    t = 1. / (1. + z / 2.)
    r = t * math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (
        0.37409196 + t * (0.09678418 + t * (-0.18628806 + t * (
            0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (
                -0.82215223 + t * 0.17087277
            )))
        )))
    )))
    return 2. - r if x < 0 else r


def cdf(x, mu=0, sigma=1):
    """Cumulative distribution function"""
    return 0.5 * erfc(-(x - mu) / (sigma * math.sqrt(2)))


def pdf(x, mu=0, sigma=1):
    """Probability density function"""
    return (1 / math.sqrt(2 * math.pi) * abs(sigma) *
            math.exp(-(((x - mu) / abs(sigma)) ** 2 / 2)))
