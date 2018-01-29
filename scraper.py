#!/usr/bin/env python

import boto3
import bs4
import checksumdir
import errno
import multiprocessing.pool
import os
import os.path
import requests
import skill
import tempfile

scraped_dir = tempfile.mkdtemp()

base_url = 'http://www.calsquash.com/boxleague/'
current_url = 's4.php?file=current.players'

bucket = 'calsquash-rankings-scraped'

def url_to_filename(url):
  if url == base_url + current_url:
    return os.path.join(scraped_dir, 'current.html')
  else:
    return os.path.join(scraped_dir, url.split('/')[-1])

# From http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as exc:
    if exc.errno == errno.EEXIST and os.path.isdir(path):
      pass
    else:
      raise

def scrape():
  mkdir_p(scraped_dir)

  # Download previous scraper state
  s3 = boto3.client('s3')
  files = s3.list_objects(Bucket=bucket)['Contents']

  def s3_download_file(f):
    key = f['Key']
    destination_path = os.path.join(scraped_dir, f['Key'])
    print 's3://%s/%s -> %s' % (bucket, key, destination_path)
    s3.download_file(bucket, key, destination_path)

  multiprocessing.pool.ThreadPool(processes=20).map(s3_download_file, files)

  print 'Scraper state hash:'
  prev_hash = checksumdir.dirhash(scraped_dir)
  print prev_hash

  # Update state with new scraped files
  changed_files = []
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

    # Don't overwrite except to update the current month
    if url != base_url + current_url and os.path.isfile(filename):
      continue

    # Fetch url
    print '%s -> %s' % (url, filename)
    r = requests.get(url)
    with open(filename, 'w') as f:
      for line in r.text.encode('utf8').splitlines(True):
        # Remove continuously-changing timestamp to enable checksumming
        if 'Generated on' not in line:
          f.write(line)
    changed_files.append(filename)

    # Look for link to previous month
    s = bs4.BeautifulSoup(r.text, 'html.parser')
    prev = [a['href'] for a in s.find_all('a')
            if a and a.string and a.string.strip() == "Last month's results here."
            and a['href']]
    if prev:
      prev_url = base_url + prev[0]
      prev_filename = url_to_filename(prev_url)
      if not os.path.isfile(prev_filename):
        urls_stack.append(prev_url)

  # Check for changes
  print 'New scraper state hash:'
  new_hash = checksumdir.dirhash(scraped_dir)
  print new_hash
  if prev_hash != new_hash:
    # Upload changed files
    for f in changed_files:
      key = os.path.basename(f)
      print '%s -> s3://%s/%s' % (f, bucket, key)
      s3.upload_file(Filename=f, Bucket=bucket, Key=key)

    skill.skill(scraped_dir)

if __name__=='__main__':
  scrape()
