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

echo "==> Buckets de la aplicación (se crean con la CLI por la restricción de AWS Academy)"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
for nombre in boletos web; do
  BUCKET="paseqr-${STAGE}-${nombre}-${ACCOUNT}"
  if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
    echo "  ya existe: $BUCKET"
  else
    aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_REGION" >/dev/null
    echo "  creado: $BUCKET"
  fi
done

echo "==> Empaquetando backend"
"$ROOT/scripts/build_backend.sh"

echo "==> Terraform ($STAGE)"
cd "$ROOT/infra"
terraform init -no-color -input=false -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="key=paseqr/${STAGE}/terraform.tfstate"
terraform apply -no-color -input=false -auto-approve -var "stage=${STAGE}"

API_URL="$(terraform output -raw api_url)"
WEB_BUCKET="$(terraform output -raw frontend_bucket)"
WEB_URL="$(terraform output -raw frontend_url)"

echo "==> Frontend"
cd "$ROOT/frontend"
npm ci --silent
VITE_API_URL="$API_URL" npm run build
aws s3 sync dist "s3://${WEB_BUCKET}" --delete --exclude index.html \
  --cache-control "public, max-age=31536000, immutable"
# index.html sin caché para que CloudFront siempre sirva la versión más reciente
aws s3 cp dist/index.html "s3://${WEB_BUCKET}/index.html" --cache-control "no-cache" --content-type "text/html"

if [ -n "${GITHUB_ACTIONS:-}" ]; then
  echo "::notice title=URLs de PaseQR::API ${API_URL} | Frontend ${WEB_URL}"
fi

echo ""
echo "Listo:"
echo "  API:      $API_URL"
echo "  Frontend: $WEB_URL"
