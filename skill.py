#!/usr/bin/env python

import bs4
import choix
import datetime
import io
import numpy as np
import os
import os.path
import prettytable
import re
import string
import sys
import tempfile

output_dir = tempfile.mkdtemp()

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
  'Peter D\xc3\xbcrr': 'Peter Duerr',
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

  Return a list of tuples (winner, loser, winner_score) if scores contains
  matching entries for (winner, loser) and (loser, winner) that sum to 7,
  indicating a successful match.

  """
  match_results = []
  for (player1, player2), winner_score in scores.items():
    if winner_score >= 4: # player1 is always winner
      loser_score = scores.get((player2, player1))
      if loser_score == 7 - winner_score:
        match_results += [(canonical_name(player1), canonical_name(player2),
                           winner_score)]
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

def parse_matches(scraped_dir):
  """Parse box league files and return match results.

  Return a chronologically-ordered list of tuples (player1, player2,
  player1_score) meaning player1 beat player2, as well as the position within
  this list corresponding to the start of the current month, and 12-month
  trailing period.

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

def calculate_ratings(matches, focus_player=None):
  """Calculate TrueSkill ratings from match history.

  matches -- a list of matches from parse_matches
  focus_player -- optionally, a player about whom to plot historical results

  Return (ratings, num_matches) where ratings maps player name to a
  trueskill.Rating object and num_matches maps player name to the number of
  played matches.
  """
  players = list(set([p for p1, p2, p1_score in matches for p in [p1, p2]]))
  player_names_to_ids = dict([(p, i) for i, p in enumerate(players)])
  num_matches = dict([(p, 0) for p in players])

  matches_by_id = []
  for p1, p2, p1_score in matches:
    p1_id = player_names_to_ids[p1]
    p2_id = player_names_to_ids[p2]
    games_for_p1 = 3
    games_for_p2 = 6 - p1_score
    matches_by_id.extend([(p1_id, p2_id)] * games_for_p1)
    matches_by_id.extend([(p2_id, p1_id)] * games_for_p2)
    num_matches[p1] += 1
    num_matches[p2] += 1

  ratings_by_id = choix.ilsr_pairwise(len(players), matches_by_id, alpha=0.01)

  ratings = dict([(players[i], r) for i, r in enumerate(ratings_by_id)])

  return ratings, num_matches

def expose(rating):
  return rating

def print_leaderboard(ratings, num_matches, outfile, ratings_1mo, ratings_12mo,
                      player_pred=None):
  """Write ratings as Markdown table to outfile, with optional player filter."""
  leaderboard = list(filter(
    player_pred, sorted(
      iter(ratings.items()), key=lambda r: expose(r[1]), reverse=True)))
  tbl = prettytable.PrettyTable()
  tbl.junction_char = '|'
  tbl.hrules = prettytable.HEADER
  tbl.field_names = ['Rank', 'Player', 'Skill', '# Matches', '1-mo \u0394 Skill', '12-mo \u0394 Skill']
  tbl.align['Rank'] = tbl.align['Skill'] = tbl.align['# Matches'] = tbl.align['1-mo \u0394 Skill'] = tbl.align['12-mo \u0394 Skill'] = 'r'
  tbl.align['Player'] = 'l'
  tbl.float_format = '.1'

  def get_prev_skill(name, prev_ratings, cur_skill):
    if name in prev_ratings:
      prev_skill = expose(prev_ratings[name])
      if abs(cur_skill - prev_skill) < 0.01:
        return None
      else:
        return prev_skill

  i = 1
  for name, rating in leaderboard:
    cur_skill = expose(rating)
    skill_1mo = get_prev_skill(name, ratings_1mo, cur_skill)
    skill_12mo = get_prev_skill(name, ratings_12mo, cur_skill)
    tbl.add_row([i, name, cur_skill, num_matches[name],
                 '%+.2f' % (cur_skill - skill_1mo) if skill_1mo else '',
                 '%+.2f' % (cur_skill - skill_12mo) if skill_12mo else ''])
    i += 1

  output_path = os.path.join(output_dir, outfile)
  with io.open(output_path, 'w', encoding='utf8') as f:
    with io.open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                              'rankings.html.template'), 'r', encoding='utf8') as template:
      f.write(string.Template(template.read()).substitute(
        filename=outfile,
        now=datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p').replace(" 0", " "),
        html_table=tbl.get_html_string()))
  print('Wrote %s.' % output_path)
  return output_path

def current_players(scraped_dir):
  """Return this month's active players."""
  players = []
  with io.open(os.path.join(scraped_dir, 'current.html'), 'r', encoding='utf8') as f:
    s = bs4.BeautifulSoup(f.read(), 'html.parser')
    for table in s.find_all('table'):
      players += [canonical_name(tr.find_all('td')[1].get_text(strip=True))
               for tr in table.find_all('tr')[1:]]
  return players

def skill(scraped_dir):
  matches, current_month_start_pos, trailing_12mo_start_pos = parse_matches(scraped_dir)
  ratings_1mo, _ = calculate_ratings(matches[0:current_month_start_pos])
  ratings_12mo, _ = calculate_ratings(matches[0:trailing_12mo_start_pos])
  ratings, num_matches = calculate_ratings(matches)
  output_files = []
  output_files.append(
    print_leaderboard(ratings, num_matches, outfile='rankings-all.html',
                      ratings_1mo=ratings_1mo, ratings_12mo=ratings_12mo))
  cau = set(current_players(scraped_dir))
  output_files.append(
    print_leaderboard(ratings, num_matches, outfile='rankings-current.html',
                    ratings_1mo=ratings_1mo, ratings_12mo=ratings_12mo,
                      player_pred=lambda r: r[0] in cau))
  return output_files
