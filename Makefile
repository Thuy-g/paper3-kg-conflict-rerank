PY := .venv/bin/python
.PHONY: install test lint format smoke slices annotation-sample clean-outputs

install:
	uv venv --python /usr/bin/python3.11 .venv
	uv pip install --python $(PY) -e ".[dev]"

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:
	$(PY) -m ruff format .
	$(PY) -m ruff check --fix .

smoke:
	$(PY) scripts/run_pilot.py --config configs/smoke.yaml

# Network-dependent; writes only to data/ (gitignored) and manifests/. Not run by tests.
slices:
	$(PY) scripts/data/slice_local_sources.py --config configs/local_slices.yaml
	$(PY) scripts/data/fetch_ragability_slice.py --config configs/ragability_slice.yaml
	$(PY) scripts/wikidata/build_reference_slice.py --config configs/wikidata_slice.yaml

# Offline; re-creates data/annotation/v1 (gitignored) and rewrites the manifest with the same items.
annotation-sample:
	$(PY) scripts/annotation/sample_items.py --config configs/annotation_v1.yaml

clean-outputs:
	rm -rf outputs/smoke
