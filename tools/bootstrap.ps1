$ErrorActionPreference = "Stop"
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-full.txt
python -m compileall -q scripts
python scripts/govern.py --ci
python -m pytest -q
Write-Host "`nRepository bootstrap complete."
