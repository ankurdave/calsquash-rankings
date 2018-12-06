import bs4
import io
import re

name_substitutions = {
  'Mike Jenson-Akula': 'Mike Jensen-Akula',
  'Michael Jensen-Akula': 'Mike Jensen-Akula',
  'Amy J. Lee': 'Amy Lee',
  'Ian McDonald': 'Ian MacDonald',
  'In Woo Cheon': 'Lucas Cheon',
  'In Woo Lucas Cheon': 'Lucas Cheon',
  'Lucas In Woo': 'Lucas Cheon',
  'Jayanthkumar Kannan': 'Jayanth Kannan',
  'Jesus Nieto Gonzalez11X2(510)612-3830': 'Jesus Nieto Gonzalez',
  'Ken-ichi Ueda': 'Ken-Ichi Ueda',
  'Keni-ichi Ueda': 'Ken-Ichi Ueda',
  u'Peter D\xc3\xbcrr': 'Peter Duerr',
  'Steve Dang': 'Stephen Dang',
  'Wladislav Ellis': 'Wladislaw Ellis',
  'David Applefield': 'David Appelfeld',
  'Saurabh Baja': 'Saurabh Bajaj',
  'Christopher Flores': 'Chris Flores',
  'Jaime Vidal': 'Jaime Perez',
  'Joseph Farrell': 'Joe Farrell',
  'Joseff Farrell': 'Joe Farrell',
}

def canonical_name(name):
  name = re.sub(r'\s+', ' ', name)
  if name in name_substitutions:
    return name_substitutions[name]
  else:
    return name

def scores_to_match_results(scores):
  """
  Validate match scores and return the results (winner and loser).

  scores -- list of tuples (player1, player2), score_of_player1

  Return a list of dicts {'winner': winner, 'loser': loser, 'winner_score':
  winner_score} if scores contains matching entries for (winner, loser) and
  (loser, winner) that sum to 7, indicating a successful match.

  """
  match_results = []
  for (player1, player2), winner_score in scores.iteritems():
    if winner_score >= 4: # player1 is always winner
      loser_score = scores.get((player2, player1))
      if loser_score == 7 - winner_score:
        match_results.append({'winner': canonical_name(player1),
                              'loser': canonical_name(player2),
                              'winner_score': winner_score})
  return match_results

def current_players(path):
  """Return this month's active players."""
  players = []
  with io.open(path, 'r', encoding='utf8') as f:
    s = bs4.BeautifulSoup(f.read(), 'html.parser')
    for table in s.find_all('table'):
      players += [canonical_name(tr.find_all('td')[1].get_text(strip=True))
               for tr in table.find_all('tr')[1:]]
  return set(players)

def parse(path):
  with io.open(path, 'r', encoding='utf8') as f:
    s = bs4.BeautifulSoup(f.read(), 'html.parser')

    matches = []
    for table in s.find_all('table'):
      names = [tr.find_all('td')[1].get_text(strip=True)
                 for tr in table.find_all('tr')[1:]]
      scores = {}
      for player1, tr in zip(names, table.find_all('tr')[1:]):
        for player2, score_cell in zip(names, tr.find_all('td')[2:-3]):
          score_text = score_cell.get_text(strip=True)
          if score_text and score_text != 'X' and re.search(r'\d+', score_text):
            score = int(re.search(r'\d+', score_text).group())
            scores[(player1, player2)] = score
      matches += scores_to_match_results(scores)

    prev = [a['href'] for a in s.find_all('a')
            if a and a.string and a.string.strip() == "Last month's results here."
            and a['href']]

    return matches, prev[0] if prev else None
