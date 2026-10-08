# Monitoreo (responsable: Juan Pablo Gutiérrez) — se completa para la Fase 3.
#
# Pendiente:
#   - 5 métricas: BoletosEmitidos y CheckIns (personalizadas, namespace "PaseQR"),
#     Errors de Lambda, latencia p95 de API Gateway, ApproximateAgeOfOldestMessage de SQS.
#   - 2 alarmas que publiquen en aws_sns_topic.alarmas:
#       * tasa de 5xx de la API > 5% en 5 minutos
#       * ApproximateNumberOfMessagesVisible de la DLQ > 0
#   - 1 dashboard (aws_cloudwatch_dashboard) con el estado del sistema.
