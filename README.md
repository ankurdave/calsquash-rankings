# Cal Squash Box League TrueSkill Rankings

Rankings of [UC Berkeley box league](http://www.calsquash.com/boxleague/s4.php?file=current.players) squash players using [TrueSkill](http://trueskill.org/).

See the rankings for [current players](rankings-current.md) and [all players](rankings-all.md).

To run:

```shell
$ pip install virtualenv

# Scrape match data from the box league records
$ ./scraper

# Generate rankings
$ ./skill
```
