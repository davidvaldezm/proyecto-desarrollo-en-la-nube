variable "region" {
  description = "Región de AWS (AWS Academy solo permite us-east-1 y us-west-2)"
  type        = string
  default     = "us-east-1"
}

variable "stage" {
  description = "Ambiente: dev o prod"
  type        = string
  default     = "dev"
}

variable "lab_role_name" {
  description = "Rol de IAM existente que usarán las Lambdas. En AWS Academy no se pueden crear roles, se usa LabRole."
  type        = string
  default     = "LabRole"
}

variable "lambda_runtime" {
  type    = string
  default = "python3.12"
}

variable "backend_build_dir" {
  description = "Carpeta con el código empaquetado del backend (la genera scripts/build_backend.sh)"
  type        = string
  default     = "../backend/build"
}

variable "alert_email" {
  description = "Correo que recibe las alarmas de CloudWatch (opcional, hay que confirmar la suscripción)"
  type        = string
  default     = ""
}
