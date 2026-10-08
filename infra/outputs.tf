output "api_url" {
  description = "URL base de la API"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "frontend_url" {
  description = "URL del sitio web"
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.bucket
}

output "boletos_bucket" {
  value = aws_s3_bucket.boletos.bucket
}

output "cola_emision_url" {
  value = aws_sqs_queue.emision.url
}

output "cola_emision_dlq_url" {
  value = aws_sqs_queue.emision_dlq.url
}

output "topico_alarmas_arn" {
  description = "Para las alarmas de CloudWatch (Flujo 3 / Monitoreo)"
  value       = aws_sns_topic.alarmas.arn
}
