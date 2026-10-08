terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.6"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # El bucket se pasa en `terraform init -backend-config=...` (ver scripts/deploy.sh),
  # porque su nombre depende de la cuenta de AWS. El estado vive en S3 para que
  # GitHub Actions y los tres integrantes compartan la misma infraestructura.
  backend "s3" {
    key          = "paseqr/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Proyecto = "PaseQR"
      Stage    = var.stage
      Curso    = "Desarrollo en la Nube ITESO"
    }
  }
}
