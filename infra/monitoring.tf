# Monitoreo (responsable: Juan Pablo Gutiérrez)
#
# 5 métricas relevantes (todas en el dashboard):
#   1. Ventas: BoletosVendidos / BoletosEmitidos / ComprasRechazadasPorCupo  (PaseQR, EMF)
#   2. Check-ins: CheckInsValidos / CheckInsRechazados por resultado         (PaseQR, EMF)
#   3. Errores de las 5 Lambdas                                               (AWS/Lambda Errors)
#   4. Latencia p95 de la API                                                 (AWS/ApiGateway Latency)
#   5. Antigüedad del mensaje más viejo en la cola de emisión                 (AWS/SQS ApproximateAgeOfOldestMessage)
# 2 alarmas -> SNS "alarmas" (correo del equipo):
#   A. Tasa de errores 5xx de la API > 5 % en 5 minutos
#   B. Mensajes en la DLQ > 0 (un boleto no se pudo emitir tras 3 intentos)

locals {
  ns     = "PaseQR"
  api_id = aws_apigatewayv2_api.http.id
  fn     = { for k, f in aws_lambda_function.fn : k => f.function_name }
}

# ---------------------------------------------------------------- Alarmas
resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name          = "${local.prefix}-api-5xx-mayor-5pct"
  alarm_description   = "Más del 5% de las peticiones a la API respondieron 5xx en 5 minutos"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 5
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarmas.arn]
  ok_actions          = [aws_sns_topic.alarmas.arn]

  metric_query {
    id          = "tasa"
    expression  = "IF(total > 0, 100 * errores / total, 0)"
    label       = "% de respuestas 5xx"
    return_data = true
  }

  metric_query {
    id = "errores"
    metric {
      namespace   = "AWS/ApiGateway"
      metric_name = "5xx"
      dimensions  = { ApiId = local.api_id }
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id = "total"
    metric {
      namespace   = "AWS/ApiGateway"
      metric_name = "Count"
      dimensions  = { ApiId = local.api_id }
      period      = 300
      stat        = "Sum"
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "dlq" {
  alarm_name          = "${local.prefix}-dlq-con-mensajes"
  alarm_description   = "Hay boletos que no se pudieron emitir tras 3 intentos (mensajes en la DLQ)"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = aws_sqs_queue.emision_dlq.name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarmas.arn]
  ok_actions          = [aws_sns_topic.alarmas.arn]
}

# ---------------------------------------------------------------- Dashboard
resource "aws_cloudwatch_dashboard" "principal" {
  dashboard_name = "${local.prefix}-estado"

  # El JSON vive en una plantilla para que sea fácil de leer y editar.
  dashboard_body = templatefile("${path.module}/dashboard.json.tftpl", {
    region    = var.region
    stage     = var.stage
    ns        = local.ns
    api_id    = local.api_id
    cola      = aws_sqs_queue.emision.name
    dlq       = aws_sqs_queue.emision_dlq.name
    alarmas   = [aws_cloudwatch_metric_alarm.api_5xx.arn, aws_cloudwatch_metric_alarm.dlq.arn]
    funciones = local.fn
  })
}
