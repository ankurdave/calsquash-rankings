#!/usr/bin/env python

import bs4
import datetime
import io
import os
import os.path
import prettytable
import re
import sys
import trueskill

env = trueskill.TrueSkill(draw_probability=0.0)

script_dir = os.path.dirname(os.path.realpath(__file__))

scraped_dir = os.path.join(script_dir, 'scraped')

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
}

def canonical_name(name):
  name = re.sub(r'\s+', ' ', name)
  if name in name_substitutions:
    return name_substitutions[name]
  else:
    return name

def scores_to_match_results(scores):
  """Validate match scores and return the results (winner and loser).

  scores -- list of tuples (player1, player2), score_of_player1

  Return a list of tuples (winner, loser) if scores contains matching entries
  for (winner, loser) and (loser, winner) that sum to 7, indicating a successful
  match.
  """
  match_results = []
  for (player1, player2), winner_score in scores.iteritems():
    if winner_score >= 4: # player1 is always winner
      loser_score = scores.get((player2, player1))
      if loser_score == 7 - winner_score:
        match_results += [(canonical_name(player1), canonical_name(player2))]
  return match_results

month_to_number = {
  'jan': 1, 'decjan': 1,
  'feb': 2,
  'mar': 3,
  'apr': 4,
  'may': 5,
  'jun': 6, 'june': 6,
  'jul': 7, 'july': 7,
  'aug': 8,
  'sep': 9, 'sept': 9,
  'oct': 10,
  'nov': 11,
  'dec': 12
}

def file_sort(filename):
  """Return chronological sort key for box league filenames."""
  if filename == 'current.html':
    return (99, 0)
  else:
    year = re.search('\d{2}', filename).group()
    month = re.search('^[a-z]+', filename).group()
    return (int(year), month_to_number[month])

def parse_matches():
  """Parse box league files and return match results.

  Return a chronologically-ordered list of tuples (player1, player2) meaning
  player1 beat player2, as well as the position within this list corresponding
  to the start of the current month, and 12-month trailing period.
  """
  matches = []

  sys.stdout.write('Parsing')
  sys.stdout.flush()
  files = sorted(os.listdir(scraped_dir), key=file_sort)
  for filename in files:
    sys.stdout.write('.')
    sys.stdout.flush()
    if filename == files[-1]:
      current_month_start_pos = len(matches)
    if filename == files[-12]:
      trailing_12mo_start_pos = len(matches)
    with io.open(os.path.join(scraped_dir, filename), 'r', encoding='utf8') as f:
      s = bs4.BeautifulSoup(f.read(), 'html.parser')
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
  sys.stdout.write('done.\n')

  return matches, current_month_start_pos, trailing_12mo_start_pos

def calculate_ratings(matches):
  """Calculate TrueSkill ratings from match history.

  matches -- a list of matches from parse_matches

  Return (ratings, num_matches) where ratings maps player name to a
  trueskill.Rating object and num_matches maps player name to the number of
  played matches.
  """
  players = set([p for ps in matches for p in ps])
  ratings = dict([(p, env.create_rating()) for p in players])
  num_matches = dict([(p, 0) for p in players])
  def add_match(p1, p2):
    ratings[p1], ratings[p2] = trueskill.rate_1vs1(ratings[p1], ratings[p2], env=env)
    num_matches[p1] += 1
    num_matches[p2] += 1
  for p1, p2 in matches:
    add_match(p1, p2)

  return ratings, num_matches

def print_leaderboard(ratings, num_matches, outfile, ratings_1mo, ratings_12mo,
                      player_pred=None):
  """Write ratings as Markdown table to outfile, with optional player filter."""
  leaderboard = filter(
    player_pred, sorted(
      ratings.iteritems(), key=lambda r: env.expose(r[1]), reverse=True))
  tbl = prettytable.PrettyTable()
  tbl.junction_char = '|'
  tbl.hrules = prettytable.HEADER
  tbl.field_names = ['Rank', 'Player', 'Skill', '# Matches', u'1-mo \u0394 Skill', u'12-mo \u0394 Skill']
  tbl.align['Rank'] = tbl.align['Skill'] = tbl.align['# Matches'] = tbl.align[u'1-mo \u0394 Skill'] = tbl.align[u'12-mo \u0394 Skill'] = 'r'
  tbl.align['Player'] = 'l'
  tbl.float_format = '.1'

  def get_prev_skill(name, prev_ratings, cur_skill):
    if name in prev_ratings:
      prev_skill = env.expose(prev_ratings[name])
      if abs(cur_skill - prev_skill) < 0.01:
        return None
      else:
        return prev_skill

  i = 1
  for name, rating in leaderboard:
    cur_skill = env.expose(rating)
    skill_1mo = get_prev_skill(name, ratings_1mo, cur_skill)
    skill_12mo = get_prev_skill(name, ratings_12mo, cur_skill)
    tbl.add_row([i, name, cur_skill, num_matches[name],
                 '%+.2f' % (cur_skill - skill_1mo) if skill_1mo else '',
                 '%+.2f' % (cur_skill - skill_12mo) if skill_12mo else ''])
    i += 1

  with io.open(os.path.join(script_dir, outfile), 'w', encoding='utf8') as f:
    f.write(u'Generated %s.\n\n' % datetime.date.today().isoformat())
    f.write(tbl.get_string())
  print 'Wrote %s.' % outfile

def competitiveness(p1, p2):
  return trueskill.quality_1vs1(ratings[p1], ratings[p2], env=env)

def current_players():
  """Return this month's active players."""
  players = []
  with io.open(os.path.join(scraped_dir, 'current.html'), 'r', encoding='utf8') as f:
    s = bs4.BeautifulSoup(f.read(), 'html.parser')
    for table in s.find_all('table'):
      players += [canonical_name(tr.find_all('td')[1].get_text(strip=True))
               for tr in table.find_all('tr')[1:]]
  return players

def main():
  matches, current_month_start_pos, trailing_12mo_start_pos = parse_matches()
  ratings_1mo, _ = calculate_ratings(matches[0:current_month_start_pos])
  ratings_12mo, _ = calculate_ratings(matches[0:trailing_12mo_start_pos])
  ratings, num_matches = calculate_ratings(matches)
  print_leaderboard(ratings, num_matches, outfile='rankings-all.md',
                    ratings_1mo=ratings_1mo, ratings_12mo=ratings_12mo)
  cau = set(current_players())
  print_leaderboard(ratings, num_matches, outfile='rankings-current.md',
                    ratings_1mo=ratings_1mo, ratings_12mo=ratings_12mo,
                    player_pred=lambda r: r[0] in cau)

if __name__=='__main__':
  main()
