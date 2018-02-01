provider "aws" {
  region     = "${var.region}"
  access_key = "${var.access_key}"
  secret_key = "${var.secret_key}"
  version    = "~> 1.7"
}

provider "archive" {
  version = "~> 1.0"
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

resource "aws_iam_role_policy_attachment" "lambda-role-can-execute-lambdas" {
  role       = "${aws_iam_role.lambda-role.name}"
  policy_arn = "arn:aws:iam::aws:policy/AWSLambdaFullAccess"
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
  filename                       = "lambda_functions.zip"
  function_name                  = "calsquash-rankings-scraper"
  role                           = "${aws_iam_role.lambda-role.arn}"
  handler                        = "scraper.scrape_and_recompute"
  runtime                        = "python2.7"
  source_code_hash               = "${base64sha256(file("lambda_functions.zip"))}"
  timeout                        = 300
  reserved_concurrent_executions = 1
}

resource "aws_cloudwatch_event_rule" "scraper-cron" {
  name                = "calsquash-rankings-scraper-event"
  description         = "Scrape calsquash-rankings and recompute rankings."
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "scraper-cron-lambda-target" {
  rule = "${aws_cloudwatch_event_rule.scraper-cron.name}"
  arn  = "${aws_lambda_function.calsquash-rankings-scraper.arn}"
}

resource "aws_lambda_permission" "allow-cloudwatch-to-call-lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.calsquash-rankings-scraper.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.scraper-cron.arn}"
}

resource "aws_dynamodb_table" "calsquash-matches-cache" {
  name           = "calsquash-matches-cache"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "filename"

  attribute {
    name = "filename"
    type = "S"
  }
}

resource "aws_dynamodb_table" "calsquash-player-stats" {
  name           = "calsquash-player-stats"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "name"

  attribute {
    name = "name"
    type = "S"
  }
}
