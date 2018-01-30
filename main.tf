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
  acl = "private"
}

data "archive_file" "lambda_functions" {
  type        = "zip"
  source_file = "scraper.py"
  source_file = "skill.py"
  source_file = "rankings.html.template"
  source_dir = ".env/lib/python2.7/site-packages/"

  output_path = "lambda_functions.zip"
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

resource "aws_iam_policy" "access-s3-bucket" {
  path = "/"
  description = "Allows access to S3 bucket for calsquash-rankings scraper and skill calculation."
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
                "s3:ListBucket"
                "s3:GetObject",
                "s3:PutObject",
            ]
        }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda-role-can-access-s3" {
  role       = "${aws_iam_role.lambda-role.name}"
  policy_arn = "${aws_iam_policy.access-s3-bucket.arn}"
}

resource "aws_lambda_function" "calsquash-rankings-scraper" {
  filename         = "${data.archive_file.lambda_functions.output_path}"
  function_name    = "calsquash-rankings-scraper"
  role             = "${aws_iam_role.lambda-role.arn}"
  handler          = "scraper.scrape"
  runtime          = "python2.7"
  source_code_hash = "${base64sha256(file("${data.archive_file.lambda_functions.output_path}"))}"
}

# resource "aws_cloudwatch_event_rule" "scraper-cron" {
#     name = "calsquash-rankings-scraper-event"
#     description = "Scrape calsquash-rankings and recompute rankings."
#     schedule_expression = "rate(1 minute)"
# }

# resource "aws_cloudwatch_event_target" "scraper-cron-lambda-target" {
#     rule = "${aws_cloudwatch_event_rule.scraper-cron.name}"
#     arn = "${aws_lambda_function.calsquash-rankings-scraper.arn}"
# }
