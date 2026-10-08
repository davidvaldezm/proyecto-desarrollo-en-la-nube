# Un solo paquete (backend/build) con todo el código; cada Lambda apunta a su handler.
data "archive_file" "backend" {
  type        = "zip"
  source_dir  = var.backend_build_dir
  output_path = "${path.module}/.build/backend.zip"
}

locals {
  lambda_env = {
    TABLA_EVENTOS         = aws_dynamodb_table.eventos.name
    TABLA_BOLETOS         = aws_dynamodb_table.boletos.name
    BUCKET_BOLETOS        = aws_s3_bucket.boletos.bucket
    COLA_EMISION_URL      = aws_sqs_queue.emision.url
    TOPICO_NOTIFICACIONES = aws_sns_topic.notificaciones.arn
    SECRETO_QR_ARN        = aws_secretsmanager_secret.qr_key.arn
    STAGE                 = var.stage
  }

  # nombre => configuración. Responsables: ver README.
  lambdas = {
    eventos        = { handler = "paseqr.handlers.eventos.handler", timeout = 10, memory = 256 }
    comprar-boleto = { handler = "paseqr.handlers.compras.handler", timeout = 10, memory = 256 }
    generar-boleto = { handler = "paseqr.handlers.generar_boleto.handler", timeout = 30, memory = 512 }
    check-in       = { handler = "paseqr.handlers.checkin.handler", timeout = 10, memory = 256 }
    recordatorios  = { handler = "paseqr.handlers.recordatorios.handler", timeout = 60, memory = 256 }
  }
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = local.lambdas
  name              = "/aws/lambda/${local.prefix}-${each.key}"
  retention_in_days = 14
}

resource "aws_lambda_function" "fn" {
  for_each = local.lambdas

  function_name    = "${local.prefix}-${each.key}"
  role             = data.aws_iam_role.lambda.arn
  runtime          = var.lambda_runtime
  handler          = each.value.handler
  timeout          = each.value.timeout
  memory_size      = each.value.memory
  filename         = data.archive_file.backend.output_path
  source_code_hash = data.archive_file.backend.output_base64sha256

  environment {
    variables = local.lambda_env
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
}

# ---------------------------------------------------------------- SQS -> generar-boleto
resource "aws_lambda_event_source_mapping" "emision" {
  event_source_arn                   = aws_sqs_queue.emision.arn
  function_name                      = aws_lambda_function.fn["generar-boleto"].arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 2
  function_response_types            = ["ReportBatchItemFailures"]
}

# ---------------------------------------------------------------- EventBridge -> recordatorios
# Se usa una regla de EventBridge (no Scheduler) porque no requiere crear un rol de IAM.
resource "aws_cloudwatch_event_rule" "recordatorios" {
  name                = "${local.prefix}-recordatorios"
  description         = "Ejecuta recordatorios y reportes de asistencia cada hora"
  schedule_expression = "rate(1 hour)"
}

resource "aws_cloudwatch_event_target" "recordatorios" {
  rule = aws_cloudwatch_event_rule.recordatorios.name
  arn  = aws_lambda_function.fn["recordatorios"].arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fn["recordatorios"].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.recordatorios.arn
}
