# Cal Squash Box League TrueSkill Rankings

Rankings of [UC Berkeley box league](http://www.calsquash.com/boxleague/s4.php?file=current.players) squash players using [TrueSkill](http://trueskill.org/).

See the rankings for [current players](https://ankurdave.com/rankings-current.html) and [all players](https://ankurdave.com/rankings-all.html).

To deploy on AWS:

1. Run `make` to prepare the Lambda function source code.

2. Install [Terraform](terraform.io) (`brew install terraform`).

3. Run `terraform init` and `terraform apply`. The latter command will prompt for your AWS access key and secret key. You can persist these values by creating a file named [`terraform.tfvars`](https://www.terraform.io/intro/getting-started/variables.html#from-a-file). See `variables.tf` for the configuration variable names.
