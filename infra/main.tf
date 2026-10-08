data "aws_caller_identity" "current" {}

# AWS Academy: no se pueden crear roles; todas las Lambdas usan LabRole.
data "aws_iam_role" "lambda" {
  name = var.lab_role_name
}

locals {
  prefix     = "paseqr-${var.stage}"
  account_id = data.aws_caller_identity.current.account_id
}

# ---------------------------------------------------------------- DynamoDB
resource "aws_dynamodb_table" "eventos" {
  name         = "${local.prefix}-eventos"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "evento_id"

  attribute {
    name = "evento_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = false
  }
}

resource "aws_dynamodb_table" "boletos" {
  name         = "${local.prefix}-boletos"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "boleto_id"

  attribute {
    name = "boleto_id"
    type = "S"
  }
  attribute {
    name = "evento_id"
    type = "S"
  }
  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "por_evento"
    hash_key        = "evento_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "por_email"
    hash_key        = "email"
    projection_type = "ALL"
  }
}

# ---------------------------------------------------------------- S3
# Boletos PDF y reportes CSV: privado, se descarga con URLs prefirmadas.
resource "aws_s3_bucket" "boletos" {
  bucket        = "${local.prefix}-boletos-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "boletos" {
  bucket                  = aws_s3_bucket.boletos.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "boletos" {
  bucket = aws_s3_bucket.boletos.id
  cors_rule {
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
  }
}

# Frontend: sitio estático público.
resource "aws_s3_bucket" "frontend" {
  bucket        = "${local.prefix}-web-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  index_document {
    suffix = "index.html"
  }
  error_document {
    key = "index.html" # rutas del SPA
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket     = aws_s3_bucket.frontend.id
  depends_on = [aws_s3_bucket_public_access_block.frontend]

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Sid       = "LecturaPublica"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
    }]
  })
}

# ---------------------------------------------------------------- SQS
resource "aws_sqs_queue" "emision_dlq" {
  name                      = "${local.prefix}-emision-dlq"
  message_retention_seconds = 1209600 # 14 días para investigar fallas
}

resource "aws_sqs_queue" "emision" {
  name                       = "${local.prefix}-emision"
  visibility_timeout_seconds = 180 # AWS recomienda 6x el timeout de la Lambda consumidora (30 s)

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.emision_dlq.arn
    maxReceiveCount     = 3
  })
}

# ---------------------------------------------------------------- SNS
resource "aws_sns_topic" "notificaciones" {
  name = "${local.prefix}-notificaciones"
}

resource "aws_sns_topic" "alarmas" {
  name = "${local.prefix}-alarmas"
}

resource "aws_sns_topic_subscription" "alarmas_email" {
  count     = var.alert_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarmas.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ---------------------------------------------------------------- Secrets Manager
resource "random_password" "qr_key" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "qr_key" {
  name                    = "${local.prefix}/qr-signing-key"
  description             = "Llave HMAC para firmar los códigos QR de los boletos"
  recovery_window_in_days = 0 # permite destruir y recrear en el laboratorio
}

resource "aws_secretsmanager_secret_version" "qr_key" {
  secret_id     = aws_secretsmanager_secret.qr_key.id
  secret_string = random_password.qr_key.result
}
