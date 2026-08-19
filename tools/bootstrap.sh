#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-full.txt
python -m compileall -q scripts
python scripts/govern.py --ci
python -m pytest -q
printf '\nRepository bootstrap complete.\n'
