#!/usr/bin/env python

import datetime
import dateutil.relativedelta
import io
import os
import os.path
import prettytable
import pytz
import re
import string
import sys
import tempfile
import time
import two_player_trueskill

output_dir = tempfile.mkdtemp()

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

def filename_to_date(filename):
  """Return date sort key for box league filenames."""
  if filename == 'current.html':
    return datetime.date.today()
  else:
    year = re.search('\d{2}', filename).group()
    month = re.search('^[a-z]+', filename).group()
    return datetime.date(2000 + int(year), month_to_number[month], 1)

def calculate_ratings(players, matches_by_date):
  """
  Calculate TrueSkill ratings from match history.

  players -- a set of player names
  matches_by_date -- a list [(match_date, [{'winner': winner_name,
 'loser': loser_name, 'winner_score': winner_score}])]

  Return a populated TwoPlayerTrueSkill instance.

  """
  ratings = two_player_trueskill.TwoPlayerTrueSkill(players)

  start = time.time()
  for date, ms in matches_by_date:
    for m in ms:
      p1, p2, p1_score = m['winner'], m['loser'], m['winner_score']
      games_for_p1 = 3
      games_for_p2 = 6 - p1_score
      ratings.update(date, p1, p2, games_for_p1, games_for_p2)

  print 'Rated %d matches in %d seconds' % (
    len([m for date, ms in matches_by_date for m in ms]),
    time.time() - start)
  return ratings

def calculate_num_matches(players, matches):
  """Return a dict {player_name: num_played_matches}."""
  num_matches = {p: 0 for p in players}
  for m in matches:
    num_matches[m['winner']] += 1
    num_matches[m['loser']] += 1
  return num_matches

def print_leaderboard(players, ratings, num_matches, outfile):
  tbl = prettytable.PrettyTable()
  tbl.junction_char = '|'
  tbl.hrules = prettytable.HEADER
  tbl.field_names = ['Rank', 'Player', 'Skill', '# Matches', u'1-mo \u0394 Skill', u'12-mo \u0394 Skill']
  tbl.align['Rank'] = tbl.align['Skill'] = tbl.align['# Matches'] = tbl.align[u'1-mo \u0394 Skill'] = tbl.align[u'12-mo \u0394 Skill'] = 'r'
  tbl.align['Player'] = 'l'
  tbl.float_format = '.1'

  def delta(x, y):
      if x is None or y is None or abs(x - y) < 0.01:
        return ''
      else:
        return '%+.2f' % (x - y)

  date_1mo_ago = datetime.date.today() + dateutil.relativedelta.relativedelta(months=-1)
  date_12mo_ago = datetime.date.today() + dateutil.relativedelta.relativedelta(months=-12)

  i = 1
  for p in ratings.get_sorted_players():
    if p in players:
      cur_skill = ratings.get_player_rating(p).expose()
      skill_change_1mo = delta(
        cur_skill, ratings.get_player_rating_at_or_before_date(p, date_1mo_ago))
      skill_change_12mo = delta(
        cur_skill, ratings.get_player_rating_at_or_before_date(p, date_12mo_ago))
      tbl.add_row([i, p, cur_skill, num_matches[p], skill_change_1mo, skill_change_12mo])
      i += 1

  output_path = os.path.join(output_dir, outfile)
  with io.open(output_path, 'w', encoding='utf8') as f:
    with io.open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                              'rankings.html.template'), 'r', encoding='utf8') as template:
      f.write(string.Template(template.read()).substitute(
        filename=outfile,
        now=datetime.datetime.now(pytz.timezone('America/Los_Angeles')).strftime('%Y-%m-%d %I:%M %p').replace(" 0", " "),
        html_table=tbl.get_html_string()))
  print 'Wrote %s.' % output_path
  return output_path

def calculate_player_history(players, matches_by_date):
  matches_by_player = {p: [] for p in players}
  for date, ms in matches_by_date:
    for m in ms:
      p1, p2, p1_score = m['winner'], m['loser'], m['winner_score']
      matches_by_player[p1].append(
        {'date': str(date), 'opponent': p2, 'outcome': 'W', 'winner_score': p1_score})
      matches_by_player[p2].append(
        {'date': str(date), 'opponent': p1, 'outcome': 'L', 'winner_score': p1_score})
  return matches_by_player

def skill(matches_by_filename, current_players, dynamodb_player_stats=None):
  matches_by_date = sorted([(filename_to_date(f), matches_by_filename[f])
                            for f in matches_by_filename.iterkeys()])

  all_matches = [m for d, ms in matches_by_date for m in ms]
  all_players = set([p for m in all_matches for p in [m['winner'], m['loser']]])

  ratings = calculate_ratings(all_players, matches_by_date)
  num_matches = calculate_num_matches(all_players, all_matches)

  output_files = []
  output_files.append(
    print_leaderboard(all_players, ratings, num_matches, outfile='rankings-all.html'))
  output_files.append(
    print_leaderboard(current_players, ratings, num_matches, outfile='rankings-current.html'))

  if dynamodb_player_stats:
    player_history = calculate_player_history(all_players, matches_by_date)
    for p in all_players:
      rating_history = [r.to_dict() for r in ratings.get_player_rating_history(p)]
      print '%s: %d ratings, %d matches -> dynamodb' % (
        p, len(rating_history), len(player_history[p]))
      dynamodb_player_stats.put_item(
        Item={'name': p,
              'ratings': rating_history,
              'matches': player_history[p]})

  return output_files
