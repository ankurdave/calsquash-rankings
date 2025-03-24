# Cal Squash Box League TrueSkill Rankings

Rankings of [UC Berkeley box league](http://www.calsquash.com/boxleague/s4.php?file=current.players) squash players using [TrueSkill Through Time](https://github.com/ankurdave/ttt-scala).

See the rankings for **[current players](https://ankurdave.com/calsquash-rankings/rankings-current.html)** and **[all players](https://ankurdave.com/calsquash-rankings/rankings-all.html)**.

## Building

To build and deploy on AWS:

1. Install dependencies: `brew install openjdk@11 sbt awscli terraform`.

2. `aws configure`. This will prompt for your AWS access key and secret key.

3. Run `make` to prepare the Lambda function source code.

4. Run `terraform init` and `terraform apply`. The latter command will prompt for your AWS access key and secret key.
