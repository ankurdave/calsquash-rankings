# Cal Squash Box League TrueSkill Rankings

Rankings of [UC Berkeley box league](http://www.calsquash.com/boxleague/s4.php?file=current.players) squash players using [TrueSkill](http://trueskill.org/). Only the match outcome (winner and loser) is used for TrueSkill; the margin of victory is ignored.

See the rankings for [current players](rankings-current.md) and [all players](rankings-all.md).

To run:

```shell
# Install dependencies
$ pip install beautifulsoup4 requests trueskill PrettyTable

# Scrape match data from the box league records
$ python scraper.py

# Generate rankings
$ python skill.py
```
