import math

# Initial mean
MU = 25.

# Initial standard deviation
SIGMA = MU / 3.

# Distance corresponding to ~76% chance of winning
BETA = SIGMA / 2.

# Dynamics factor
TAU = SIGMA / 100.

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
        winner_cur_rating = self.ratings[winner]
        loser_cur_rating = self.ratings[loser]
        self.ratings[winner] = self.calc_new_rating(
            winner_cur_rating, loser_cur_rating, a_won=True)
        self.ratings[loser] = self.calc_new_rating(
            loser_cur_rating, winner_cur_rating, a_won=False)

    def get_ratings(self):
        return {p: r.expose() for p, r in self.ratings.iteritems()}

    def calc_new_rating(self, a_rating, b_rating, a_won):
        c = math.sqrt(square(a_rating.sigma)
                    + square(b_rating.sigma)
                    + 2. * square(BETA))

        if a_won:
            diff = (a_rating.mu - b_rating.mu) / c
        else:
            diff = (b_rating.mu - a_rating.mu) / c

        denom = cdf(diff)
        v = pdf(diff) / denom if denom else -diff
        w = v * (v + diff)
        assert(0 < w < 1)

        rank_multiplier = 1. if a_won else -1.

        mean_multiplier = (square(a_rating.sigma) + square(TAU)) / c

        variance_with_dynamics = square(a_rating.sigma) + square(TAU)
        std_dev_multiplier = variance_with_dynamics / square(c)

        return Rating(a_rating.mu + rank_multiplier * mean_multiplier * v,
                      math.sqrt(variance_with_dynamics * (1. - w * std_dev_multiplier)))

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
