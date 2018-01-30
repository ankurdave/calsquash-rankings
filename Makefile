lambda_functions.zip: .env/lib/python2.7/site-packages scraper.py skill.py rankings.html.template
	zip lambda_functions.zip scraper.py skill.py rankings.html.template
	cd .env/lib/python2.7/site-packages/ && zip -ru ../../../../lambda_functions.zip *

.env/lib/python2.7/site-packages: requirements.txt
	virtualenv .env
	source .env/bin/activate && pip install -q -r requirements.txt

clean:
	rm -r .env lambda_functions.zip
