#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "  Installing Reference-Driven Design Skill (Antigravity/AI) "
echo "============================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.gemini/config/skills/reference-driven-design"

echo "[1/3] Installing Python dependencies (Pillow, PyMuPDF, python-pptx)..."
python3 -m pip install -r "${SCRIPT_DIR}/requirements.txt"

echo "[2/3] Copying skill files to ${TARGET_DIR}..."
mkdir -p "${TARGET_DIR}"
cp -R "${SCRIPT_DIR}/skills/reference-driven-design/"* "${TARGET_DIR}/"

echo "[3/3] Verifying installation..."
python3 "${TARGET_DIR}/scripts/fetch_references.py" --help >/dev/null
python3 "${TARGET_DIR}/scripts/export_presentation.py" --help >/dev/null

echo "[OK] Reference-Driven Design skill installed at: ${TARGET_DIR}"
