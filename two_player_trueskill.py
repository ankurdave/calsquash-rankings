import glicko2

class TwoPlayerTrueSkill:
    """"Specialized implementation of TrueSkill for two-player games with zero
    draw probability.

    Derived from
    https://github.com/moserware/Skills/blob/master/Skills/TrueSkill/TwoPlayerTrueSkillCalculator.cs."""

    def __init__(self, players):
        self.glicko2 = glicko2.Glicko2()
        self.players = players
        self.ratings = dict([(p, self.glicko2.create_rating()) for p in players])

    def update(self, matches):
        matches_by_player = {p: [] for p in self.players}

        for m in matches:
            p1, p2, p1_score = m['winner'], m['loser'], m['winner_score']
            games_for_p1 = 3
            games_for_p2 = 6 - p1_score

            for i in range(games_for_p1):
                matches_by_player[p1].append((glicko2.WIN, self.ratings[p2]))
                matches_by_player[p2].append((glicko2.LOSS, self.ratings[p1]))
            for i in range(games_for_p2):
                matches_by_player[p2].append((glicko2.WIN, self.ratings[p1]))
                matches_by_player[p1].append((glicko2.LOSS, self.ratings[p2]))

        for p, updates in matches_by_player.iteritems():
            self.ratings[p] = self.glicko2.rate(self.ratings[p], updates)

    def get_ratings(self):
        return {p: r.mu - 2. * r.phi for p, r in self.ratings.iteritems()}
