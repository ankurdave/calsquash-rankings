#!/usr/bin/env python

import boto3
import bs4
import errno
import hashlib
import os
import os.path
import parser
import requests
import skill
import tempfile

scraped_dir = tempfile.mkdtemp()

base_url = 'http://www.calsquash.com/boxleague/'
current_url = 's4.php?file=current.players'

rankings_bucket = 'ankurdave.com'

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
dynamodb_match_cache = dynamodb.Table('calsquash-matches-cache')
dynamodb_player_stats = dynamodb.Table('calsquash-player-stats')

def url_to_filename(url):
  if url == base_url + current_url:
    return 'current.html'
  else:
    return url.split('/')[-1]

def download_url(url, path):
  print '%s -> %s' % (url, path)
  r = requests.get(url)
  with open(path, 'w') as f:
    for line in r.text.encode('utf8').splitlines(True):
      # Remove continuously-changing timestamp to enable checksumming
      if 'Generated on' not in line:
        f.write(line)

def file_hash(filename):
  return hashlib.sha256(open(filename, 'rb').read()).hexdigest()

def check_for_new_games():
  prev_entry = dynamodb_match_cache.get_item(
    Key={'filename': 'current.html'})
  prev_hash = (prev_entry['Item']['hash']
               if 'Item' in prev_entry
               and 'hash' in prev_entry['Item']
               else None)
  print 'dynamodb -> hash %s' % prev_hash

  url = base_url + current_url
  path = os.path.join(scraped_dir, 'current.html')
  download_url(url, path)

  new_hash = file_hash(path)
  new_games_added = new_hash != prev_hash
  if new_games_added:
    print 'hash %s -> dynamodb' % new_hash
    dynamodb_match_cache.put_item(
      Item={'filename': 'current.html', 'hash': new_hash})

  return new_games_added

def fetch_dynamo_cached_matches():
  return {elem['filename']: elem for elem in dynamodb_match_cache.scan()['Items']}

def scrape():
  dynamo_elems = fetch_dynamo_cached_matches()
  matches = {}

  seed_urls = [
    'jul03.html', 'aug03.html', 'sep03.html', 'oct03.html', 'nov03.html',
    'feb04.html', 'mar04.html', 'apr04.html', 'may04.html', 'jun04.html',
    'jul04.html', 'oct04.html', 'nov04.html', 'jan05.html', 'feb05.html',
    'june06.html', 'jul09.html', 'sep09.html', 'nov09.html', 'sep12.html',
    current_url]

  urls_stack = [base_url + u for u in seed_urls]
  while urls_stack:
    url = urls_stack.pop()
    filename = url_to_filename(url)

    if filename in matches:
      print '%s: already seen' % filename
      continue
    elif filename in dynamo_elems and filename != 'current.html':
      print '%s: in dynamo cache' % filename
      matches[filename] = dynamo_elems[filename]['matches']
      if ('prev_filename' in dynamo_elems[filename]
          and dynamo_elems[filename]['prev_filename']):
        urls_stack.append(base_url + dynamo_elems[filename]['prev_filename'])
    else:
      print '%s: needs fetch' % filename
      path = os.path.join(scraped_dir, filename)
      if not os.path.isfile(path):
        download_url(url, path)

      file_matches, prev_url = parser.parse(path)
      matches[filename] = file_matches
      prev_filename = url_to_filename(prev_url) if prev_url else None

      if filename != 'current.html':
        print '%s (%d matches, %s prev) -> dynamodb' % (
          filename, len(file_matches), prev_filename)
        dynamodb_match_cache.put_item(
          Item={'filename': filename, 'matches': file_matches,
                'prev_filename': prev_filename})

      if prev_url:
        urls_stack.append(base_url + prev_url)

  return matches

def upload_rankings(files):
  for f in files:
    key = os.path.basename(f)
    print '%s -> s3://%s/%s' % (f, rankings_bucket, key)
    s3.upload_file(Filename=f, Bucket=rankings_bucket, Key=key,
                   ExtraArgs={'ContentType': 'text/html',
                              'CacheControl': 'no-cache'})

def scrape_and_recompute(event=None, context=None):
  if check_for_new_games():
    matches = scrape()
    current_players = parser.current_players(os.path.join(scraped_dir, 'current.html'))
    ranking_files = skill.skill(matches, current_players)
    upload_rankings(ranking_files)
  else:
    print 'No new games'

if __name__ == '__main__':
  scrape_and_recompute()
