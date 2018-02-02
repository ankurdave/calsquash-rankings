provider "aws" {
  region     = "${var.region}"
  access_key = "${var.access_key}"
  secret_key = "${var.secret_key}"
  version    = "~> 1.7"
}

provider "archive" {
  version = "~> 1.0"
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
  write_capacity = 1
  hash_key       = "filename"

  attribute {
    name = "filename"
    type = "S"
  }
}

resource "aws_dynamodb_table" "calsquash-player-stats" {
  name           = "calsquash-player-stats"
  read_capacity  = 5
  write_capacity = 15
  hash_key       = "name"

  attribute {
    name = "name"
    type = "S"
  }
}

resource "aws_lambda_function" "calsquash-render-player-stats" {
  filename         = "lambda_functions.zip"
  function_name    = "calsquash-render-player-stats"
  role             = "${aws_iam_role.lambda-role.arn}"
  handler          = "player_stats.render"
  runtime          = "python2.7"
  source_code_hash = "${base64sha256(file("lambda_functions.zip"))}"
  timeout          = 5
}

resource "aws_api_gateway_rest_api" "calsquash-stats-api" {
  name = "calsquash-stats-api"
}

resource "aws_api_gateway_deployment" "calsquash-stats-api-deployment" {
  depends_on = [
    "aws_api_gateway_method.player-stats-GET",
    "aws_api_gateway_integration.player-stats-GET-from-lambda",
    "aws_api_gateway_integration_response.player-stats-GET",
    "aws_api_gateway_method_response.player-stats-GET",
  ]

  rest_api_id = "${aws_api_gateway_rest_api.calsquash-stats-api.id}"
  stage_name  = "prod"
}

resource "aws_api_gateway_resource" "player-stats" {
  rest_api_id = "${aws_api_gateway_rest_api.calsquash-stats-api.id}"
  parent_id   = "${aws_api_gateway_rest_api.calsquash-stats-api.root_resource_id}"
  path_part   = "player-stats"
}

resource "aws_api_gateway_method" "player-stats-GET" {
  rest_api_id   = "${aws_api_gateway_rest_api.calsquash-stats-api.id}"
  resource_id   = "${aws_api_gateway_resource.player-stats.id}"
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.querystring.name" = true
  }

  request_validator_id = "${aws_api_gateway_request_validator.player-stats-GET-validate-querystring.id}"
}

resource "aws_api_gateway_request_validator" "player-stats-GET-validate-querystring" {
  rest_api_id                 = "${aws_api_gateway_rest_api.calsquash-stats-api.id}"
  name                        = "player-stats-GET-validate-querystring"
  validate_request_parameters = true
}

resource "aws_api_gateway_integration" "player-stats-GET-from-lambda" {
  rest_api_id             = "${aws_api_gateway_rest_api.calsquash-stats-api.id}"
  resource_id             = "${aws_api_gateway_resource.player-stats.id}"
  http_method             = "${aws_api_gateway_method.player-stats-GET.http_method}"
  type                    = "AWS"
  integration_http_method = "POST"
  uri                     = "arn:aws:apigateway:${var.region}:lambda:path/2015-03-31/functions/${aws_lambda_function.calsquash-render-player-stats.arn}/invocations"
  credentials             = "${aws_iam_role.lambda-role.arn}"

  request_templates = {
    "application/json" = <<EOF
{
    "name": "$input.params('name')"
}
EOF
  }

  passthrough_behavior = "NEVER"
}

resource "aws_api_gateway_integration_response" "player-stats-GET" {
  rest_api_id = "${aws_api_gateway_rest_api.calsquash-stats-api.id}"
  resource_id = "${aws_api_gateway_resource.player-stats.id}"
  http_method = "${aws_api_gateway_method.player-stats-GET.http_method}"
  status_code = "${aws_api_gateway_method_response.player-stats-GET.status_code}"

  response_templates = {
    "text/html" = <<EOF
#set($inputRoot = $input.path('$'))
$inputRoot"
EOF
  }

  depends_on = ["aws_api_gateway_integration.player-stats-GET-from-lambda"]
}

resource "aws_api_gateway_method_response" "player-stats-GET" {
  rest_api_id = "${aws_api_gateway_rest_api.calsquash-stats-api.id}"
  resource_id = "${aws_api_gateway_resource.player-stats.id}"
  http_method = "${aws_api_gateway_method.player-stats-GET.http_method}"
  status_code = "200"

  response_models = {
    "text/html" = "Empty"
  }
}

locals {
  player_stats_url = "https://${aws_api_gateway_deployment.calsquash-stats-api-deployment.rest_api_id}.execute-api.${var.region}.amazonaws.com/${aws_api_gateway_deployment.calsquash-stats-api-deployment.stage_name}${aws_api_gateway_resource.player-stats.path}"
}

output "player_stats_url" {
  value = "${local.player_stats_url}"
}

resource "aws_lambda_function" "calsquash-publish-player-stats" {
  filename         = "lambda_functions.zip"
  function_name    = "calsquash-publish-player-stats"
  role             = "${aws_iam_role.lambda-role.arn}"
  handler          = "scraper.publish_player_stats"
  runtime          = "python2.7"
  source_code_hash = "${base64sha256(file("lambda_functions.zip"))}"
  timeout          = 300
}

resource "aws_s3_bucket_object" "css" {
  bucket       = "ankurdave.com"
  key          = "calsquash-rankings-style.css"
  source       = "calsquash-rankings-style.css"
  etag         = "${md5(file("calsquash-rankings-style.css"))}"
  acl          = "public-read"
  content_type = "text/css"
}

resource "aws_cloudwatch_event_rule" "player-stats-cron" {
  name                = "calsquash-rankings-player-stats-event"
  description         = "Scrape calsquash-rankings and recompute player stats."
  schedule_expression = "rate(1 day)"
}

resource "aws_cloudwatch_event_target" "player-stats-cron-lambda-target" {
  rule = "${aws_cloudwatch_event_rule.player-stats-cron.name}"
  arn  = "${aws_lambda_function.calsquash-publish-player-stats.arn}"
}

resource "aws_lambda_permission" "allow-cloudwatch-to-call-lambda-2" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.calsquash-publish-player-stats.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.player-stats-cron.arn}"
}
