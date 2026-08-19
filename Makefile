.PHONY: install compile test check watch demo-add demo-breaking demo-patch reset docker-check clean

install:
	python -m pip install -r requirements-full.txt

compile:
	python -m compileall -q scripts

test:
	python -m pytest -q

check:
	python scripts/govern.py --ci

watch:
	python scripts/watch.py

demo-add:
	python scripts/demo_change.py add-class
	python scripts/govern.py

demo-breaking:
	python scripts/demo_change.py reset
	python scripts/demo_change.py breaking-superclass
	python scripts/govern.py

demo-patch:
	python scripts/demo_change.py reset
	python scripts/demo_change.py annotation-only
	python scripts/govern.py

reset:
	python scripts/demo_change.py reset

docker-check:
	docker compose run --rm governance

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
