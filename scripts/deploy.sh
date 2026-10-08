#!/usr/bin/env bash
# Despliegue completo: estado de Terraform → backend → infraestructura → frontend.
# Requisitos: aws CLI con credenciales activas, terraform >= 1.10, python 3.12, node 20.
# Uso: ./scripts/deploy.sh [stage]     (stage por defecto: dev)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="${1:-${STAGE:-dev}}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

echo "==> Cuenta de AWS"
aws sts get-caller-identity --output table

echo "==> Bucket de estado"
STATE_BUCKET="$("$ROOT/scripts/bootstrap.sh" | tail -n 1)"

echo "==> Empaquetando backend"
"$ROOT/scripts/build_backend.sh"

echo "==> Terraform ($STAGE)"
cd "$ROOT/infra"
terraform init -input=false -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="key=paseqr/${STAGE}/terraform.tfstate"
terraform apply -input=false -auto-approve -var "stage=${STAGE}"

API_URL="$(terraform output -raw api_url)"
WEB_BUCKET="$(terraform output -raw frontend_bucket)"
WEB_URL="$(terraform output -raw frontend_url)"

echo "==> Frontend"
cd "$ROOT/frontend"
npm ci --silent
VITE_API_URL="$API_URL" npm run build
aws s3 sync dist "s3://${WEB_BUCKET}" --delete

echo ""
echo "Listo:"
echo "  API:      $API_URL"
echo "  Frontend: $WEB_URL"
