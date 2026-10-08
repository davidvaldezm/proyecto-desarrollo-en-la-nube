#!/usr/bin/env bash
# Empaqueta el backend en backend/build: código + dependencias compiladas para Lambda (Linux x86_64, Python 3.12).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/backend/build"

rm -rf "$BUILD"
mkdir -p "$BUILD"

if grep -qvE '^\s*(#|$)' "$ROOT/backend/requirements.txt"; then
  pip install -q -r "$ROOT/backend/requirements.txt" -t "$BUILD" \
    --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 \
    --only-binary=:all: --upgrade
fi

cp -r "$ROOT/backend/src/paseqr" "$BUILD/"
find "$BUILD" -name '__pycache__' -type d -prune -exec rm -rf {} +
echo "Backend empaquetado en $BUILD"
