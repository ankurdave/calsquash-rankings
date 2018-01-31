#!/usr/bin/env python

import datetime
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

def file_sort(filename):
  """Return chronological sort key for box league filenames."""
  if filename == 'current.html':
    return (99, 0)
  else:
    year = re.search('\d{2}', filename).group()
    month = re.search('^[a-z]+', filename).group()
    return (int(year), month_to_number[month])

def calculate_ratings(matches):
  """
  Calculate TrueSkill ratings from match history.

  matches -- a list of matches, each a dict {'winner': winner, 'loser': loser,
  'winner_score': winner_score}

  Return (ratings, num_matches) where ratings maps player name to a
  numerical rating and num_matches maps player name to the number of
  played matches.

  """
  players = set([p for m in matches for p in [m['winner'], m['loser']]])
  trueskill = two_player_trueskill.TwoPlayerTrueSkill(players)
  num_matches = {p: 0 for p in players}

  start = time.time()
  for m in matches:
    p1, p2, p1_score = m['winner'], m['loser'], m['winner_score']
    games_for_p1 = 3
    games_for_p2 = 6 - p1_score
    for i in range(games_for_p1):
      trueskill.update(p1, p2)
    for i in range(games_for_p2):
      trueskill.update(p2, p1)
    num_matches[p1] += 1
    num_matches[p2] += 1

  print 'Rated %d matches in %d seconds' % (len(matches), time.time() - start)
  return trueskill.get_ratings(), num_matches

def print_leaderboard(ratings, num_matches, outfile, ratings_1mo, ratings_12mo,
                      player_pred=None):
  """Write ratings as Markdown table to outfile, with optional player filter."""
  leaderboard = filter(
    player_pred, sorted(
      ratings.iteritems(), key=lambda r: r[1], reverse=True))
  tbl = prettytable.PrettyTable()
  tbl.junction_char = '|'
  tbl.hrules = prettytable.HEADER
  tbl.field_names = ['Rank', 'Player', 'Skill', '# Matches', u'1-mo \u0394 Skill', u'12-mo \u0394 Skill']
  tbl.align['Rank'] = tbl.align['Skill'] = tbl.align['# Matches'] = tbl.align[u'1-mo \u0394 Skill'] = tbl.align[u'12-mo \u0394 Skill'] = 'r'
  tbl.align['Player'] = 'l'
  tbl.float_format = '.1'

  def get_prev_skill(name, prev_ratings, cur_skill):
    if name in prev_ratings:
      prev_skill = prev_ratings[name]
      if abs(cur_skill - prev_skill) < 0.01:
        return None
      else:
        return prev_skill

  i = 1
  for name, rating in leaderboard:
    cur_skill = rating
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
        now=datetime.datetime.now(pytz.timezone('America/Los_Angeles')).strftime('%Y-%m-%d %I:%M %p').replace(" 0", " "),
        html_table=tbl.get_html_string()))
  print 'Wrote %s.' % output_path
  return output_path

def skill(matches_by_filename, current_players):
  filenames = sorted(matches_by_filename.keys(), key=file_sort)
  filenames_until_current_month = filenames[0:-1]
  filenames_until_trailing_12mo = filenames[0:-12]
  def matches_for_filename_list(fs):
    return [m for f in fs for m in matches_by_filename[f]]

  all_matches = matches_for_filename_list(filenames)
  matches_1mo = matches_for_filename_list(filenames_until_current_month)
  matches_12mo = matches_for_filename_list(filenames_until_trailing_12mo)

  ratings, num_matches = calculate_ratings(all_matches)
  ratings_1mo, _ = calculate_ratings(matches_1mo)
  ratings_12mo, _ = calculate_ratings(matches_12mo)

  output_files = []
  output_files.append(
    print_leaderboard(ratings, num_matches, outfile='rankings-all.html',
                      ratings_1mo=ratings_1mo, ratings_12mo=ratings_12mo))
  output_files.append(
    print_leaderboard(ratings, num_matches, outfile='rankings-current.html',
                      ratings_1mo=ratings_1mo, ratings_12mo=ratings_12mo,
                      player_pred=lambda r: r[0] in current_players))
  return output_files
