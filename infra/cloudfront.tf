# HTTPS para el frontend: los navegadores solo permiten usar la cámara (escáner de QR)
# y crypto.randomUUID en sitios seguros. El origen es el sitio estático de S3.
resource "aws_cloudfront_distribution" "web" {
  count = var.habilitar_cloudfront ? 1 : 0

  enabled             = true
  comment             = "${local.prefix} frontend"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  wait_for_deployment = false

  origin {
    domain_name = aws_s3_bucket_website_configuration.frontend.website_endpoint
    origin_id   = "s3-web"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "s3-web"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

locals {
  frontend_url = var.habilitar_cloudfront ? "https://${aws_cloudfront_distribution.web[0].domain_name}" : "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}
