provider "aws" {
  region     = "${var.region}"
  access_key = "${var.access_key}"
  secret_key = "${var.secret_key}"
}

terraform {
    required_providers {
        aws = {
            source = "hashicorp/aws"
            version = "~> 4.29.0"
        }
        archive = {
            version = "~> 1.0"
        }
    }
    backend "s3" {
        bucket = "ankurdave-aws-config"
        key = "calsquash-rankings.tfstate"
        region = "us-east-1"
    }
}

data "aws_iam_policy_document" "assume-role-for-apigateway-and-lambda" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com", "lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda-role" {
  assume_role_policy = "${data.aws_iam_policy_document.assume-role-for-apigateway-and-lambda.json}"
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
                "arn:aws:s3:::ankurdave.com/calsquash-rankings/rankings-all.html",
                "arn:aws:s3:::ankurdave.com/calsquash-rankings/rankings-current.html",
                "arn:aws:s3:::ankurdave.com/calsquash-rankings/player-stats/*"
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
  runtime                        = "python3.9"
  source_code_hash               = "${filebase64sha256("lambda_functions.zip")}"
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
  write_capacity = 1
  hash_key       = "filename"

  attribute {
    name = "filename"
    type = "S"
  }
}

resource "aws_lambda_function" "calsquash-publish-player-stats" {
  filename         = "player-stats/target/scala-2.12/calsquash-rankings-assembly-0.1.jar"
  function_name    = "calsquash-publish-player-stats"
  role             = "${aws_iam_role.lambda-role.arn}"
  handler          = "com.ankurdave.calsquashrankings.NewMatchHandler::handleRequest"
  runtime          = "java8"
  source_code_hash = "${filebase64sha256("player-stats/target/scala-2.12/calsquash-rankings-assembly-0.1.jar")}"
  timeout          = 300
  memory_size      = 1024
}

resource "aws_s3_object" "css" {
  bucket       = "ankurdave.com"
  key          = "calsquash-rankings-style.css"
  source       = "calsquash-rankings-style.css"
  etag         = "${filemd5("calsquash-rankings-style.css")}"
  acl          = "public-read"
  content_type = "text/css"
}

resource "aws_s3_object" "js" {
  bucket       = "ankurdave.com"
  key          = "calsquash-rankings/player-stats/player-stats-chart.js"
  source       = "player-stats-chart.js"
  etag         = "${filemd5("player-stats-chart.js")}"
  acl          = "public-read"
  content_type = "text/javascript"
}

resource "aws_lambda_permission" "allow-lambda-to-call-player-stats" {
  statement_id  = "AllowInvokeLambdaFromLambda"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.calsquash-publish-player-stats.function_name}"
  principal     = "lambda.amazonaws.com"
}

