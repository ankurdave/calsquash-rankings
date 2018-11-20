import boto3
import datetime
import dateutil
import json
import io
import os
import re
import string
import urllib

def player_stats_link(player_name):
    return '<a href="player-stats?%s">%s</a>' % (
        urllib.urlencode({'name': player_name}), player_name)

def render(event, context):
    player_name = event['name']

    dynamodb = boto3.resource('dynamodb')
    dynamodb_player_stats = dynamodb.Table('calsquash-player-stats')

    response = dynamodb_player_stats.get_item(Key={'name': player_name})
    if 'Item' not in response:
        return 'No such player'
    player_stats = response['Item']

    # Match stats
    num_matches = len(player_stats['matches'])

    # Match history and opponent ratings
    rows = []
    rating_data = []
    def add_header(fields):
        rows.append('<tr>%s</tr>' % ''.join(['<th>%s</th>' % (f,) for f in fields]))
    def add_row(fields):
        rows.append('<tr>%s</tr>' % ''.join(['<td>%s</td>' % (f,) for f in fields]))

    add_header(['Date', 'Opponent', 'Outcome'])

    for m in reversed(player_stats['matches']):
        date = datetime.datetime.strptime(m['date'], '%Y-%m-%d')
        outcome = '%s 3-%d' % (
            'Won' if m['outcome'] == 'W' else 'Lost',
            6 - m['winner_score'])
        add_row([date.strftime('%b %Y'), player_stats_link(m['opponent']), outcome])

        rating_data.append(
            ('''[new Date(%d, %d, %d), null, null, null, null, null, %f, %s]'''
             if m['outcome'] == 'W' else
             '''[new Date(%d, %d, %d), null, null, null, %f, %s, null, null]''') % (
                 date.year, date.month - 1, date.day,
                 m['opponent_mu'], json.dumps(m['opponent'])))

    html_table = '\n'.join(['<table>'] + rows + ['</table>'])

    # Rating history
    for r in player_stats['ratings']:
        if r['date'] != 'None':
            date = datetime.datetime.strptime(r['date'], '%Y-%m-%d')

            mu = float(r['mu'])
            sigma = float(r['sigma'])
            rating_data.append('[new Date(%d, %d, %d), %f, %f, %f, null, null, null, null]' % (
                date.year, date.month - 1, date.day,
                mu, mu - 3. * sigma, mu + 3. * sigma))

    player_stats_template_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'player-stats.html.template')
    with io.open(player_stats_template_path, 'r', encoding='utf8') as template:
        html = string.Template(template.read()).substitute(
            player_name=player_name,
            rating_data=',\n'.join(rating_data),
            num_matches=num_matches,
            match_history_table=html_table)
        return html

if __name__ == '__main__':
    print(render({'name': 'Ankur Dave'}, None))
