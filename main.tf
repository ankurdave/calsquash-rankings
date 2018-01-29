provider "aws" {
  region     = "${var.region}"
  access_key = "${var.access_key}"
  secret_key = "${var.secret_key}"
  version    = "~> 1.7"
}

provider "archive" {
  version = "~> 1.0"
}

resource "aws_s3_bucket" "calsquash-rankings-scraped" {
  bucket = "calsquash-rankings-scraped"
  acl    = "private"
}

data "aws_iam_policy_document" "assume-role-for-lambda" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda-role" {
  assume_role_policy = "${data.aws_iam_policy_document.assume-role-for-lambda.json}"
}

resource "aws_iam_policy" "access-state-s3-bucket" {
  path        = "/"
  description = "Allows access to S3 bucket for calsquash-rankings scraper and skill calculation state."

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Resource": [
                "${aws_s3_bucket.calsquash-rankings-scraped.arn}",
                "${aws_s3_bucket.calsquash-rankings-scraped.arn}/*"
            ],
            "Action": [
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject"
            ]
        }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda-role-can-access-state-in-s3" {
  role       = "${aws_iam_role.lambda-role.name}"
  policy_arn = "${aws_iam_policy.access-state-s3-bucket.arn}"
}

resource "aws_iam_policy" "access-output-s3-files" {
  path        = "/"
  description = "Allows access to S3 files for rankings output."

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Resource": [
                "arn:aws:s3:::ankurdave.com/rankings-all.html",
                "arn:aws:s3:::ankurdave.com/rankings-current.html"
            ],
            "Action": [
                "s3:PutObject"
            ]
        }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda-role-can-write-output-to-s3" {
  role       = "${aws_iam_role.lambda-role.name}"
  policy_arn = "${aws_iam_policy.access-output-s3-files.arn}"
}

resource "aws_lambda_function" "calsquash-rankings-scraper" {
  filename         = "lambda_functions.zip"
  function_name    = "calsquash-rankings-scraper"
  role             = "${aws_iam_role.lambda-role.arn}"
  handler          = "scraper.scrape_and_recompute"
  runtime          = "python2.7"
  source_code_hash = "${base64sha256(file("lambda_functions.zip"))}"
  timeout          = 300
}

resource "aws_cloudwatch_event_rule" "scraper-cron" {
    name = "calsquash-rankings-scraper-event"
    description = "Scrape calsquash-rankings and recompute rankings."
    schedule_expression = "rate(2 minutes)"
}


resource "aws_cloudwatch_event_target" "scraper-cron-lambda-target" {
    rule = "${aws_cloudwatch_event_rule.scraper-cron.name}"
    arn = "${aws_lambda_function.calsquash-rankings-scraper.arn}"
}
