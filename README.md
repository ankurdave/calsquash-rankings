# Cal Squash Box League TrueSkill Rankings

Rankings of [UC Berkeley box league](http://www.calsquash.com/boxleague/s4.php?file=current.players) squash players using [TrueSkill](https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/).

See the rankings for **[current players](https://ankurdave.com/calsquash-rankings/rankings-current.html)** and **[all players](https://ankurdave.com/calsquash-rankings/rankings-all.html)**.

## Building

To build and deploy on AWS:

1. Run `make` to prepare the Lambda function source code.

2. Install [Terraform](https://www.terraform.io/) (`brew install terraform`).

3. Run `terraform init` and `terraform apply`. The latter command will prompt for your AWS access key and secret key. You can persist these values by creating a file named [`terraform.tfvars`](https://www.terraform.io/intro/getting-started/variables.html#from-a-file). See `variables.tf` for the configuration variable names.
