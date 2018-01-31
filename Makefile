lambda_functions.zip: .env/lib/python2.7/site-packages scraper.py parser.py skill.py two_player_trueskill.py rankings.html.template
	rm -f lambda_functions.zip
	zip lambda_functions.zip scraper.py parser.py skill.py two_player_trueskill.py rankings.html.template
	cd .env/lib/python2.7/site-packages/ && zip -ru ../../../../lambda_functions.zip *
	zip -d lambda_functions.zip 'botocore/*' 'pip/*' 'docutils/*' 'boto3/*'

.env/lib/python2.7/site-packages: requirements.txt
	virtualenv .env
	source .env/bin/activate && pip install -q -r requirements.txt

clean:
	rm -r .env lambda_functions.zip
