#!/usr/bin/env bash
# Elimina toda la infraestructura de un stage (no borra el bucket de estado).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="${1:-${STAGE:-dev}}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"

[ -d "$ROOT/backend/build" ] || "$ROOT/scripts/build_backend.sh"
cd "$ROOT/infra"
terraform init -input=false -reconfigure \
  -backend-config="bucket=paseqr-tfstate-${ACCOUNT}" \
  -backend-config="key=paseqr/${STAGE}/terraform.tfstate"
terraform destroy -input=false -auto-approve -var "stage=${STAGE}"
