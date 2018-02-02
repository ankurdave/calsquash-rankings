all: lambda_functions.zip
.PHONY: all

PY_PACKAGE_DIR = lambda_functions/.env/lib/python2.7/site-packages
LAMBDA_SOURCES = \
	scraper.py \
	parser.py \
	skill.py \
	two_player_trueskill.py \
	player_stats.py \
	rankings.html.template \
	player-stats.html.template

lambda_functions.zip: $(PY_PACKAGE_DIR) $(addprefix lambda_functions/,$(LAMBDA_SOURCES))
	rm -f lambda_functions.zip
	cd lambda_functions && zip ../lambda_functions.zip $(LAMBDA_SOURCES)
	cd $(PY_PACKAGE_DIR) && zip -ru ../../../../../lambda_functions.zip *
	zip -d lambda_functions.zip 'botocore/*' 'pip/*' 'docutils/*' 'boto3/*'

$(PY_PACKAGE_DIR): lambda_functions/requirements.txt
	cd lambda_functions && virtualenv .env
	cd lambda_functions && source .env/bin/activate && pip install -q -r requirements.txt

clean:
	rm -rf lambda_functions/.env lambda_functions.zip
