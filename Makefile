.PHONY: help install extract manifest bundle llms-full search-index collection-index coverage review review-stats vocab sitemap test validate schema determinism check

UV ?= uv

help:
	@echo "Available targets:"
	@echo "  install      Sync uv development dependencies"
	@echo "  extract      Re-extract objects/ from SRD_CC_v5.2.1.md"
	@echo "  manifest     Rebuild the aggregate JSON-LD manifest"
	@echo "  bundle       Build the single-file JSON-LD corpus"
	@echo "  llms-full    Regenerate llms-full.txt"
	@echo "  search-index Regenerate objects/search-index.json"
	@echo "  test         Run the structural test suite"
	@echo "  validate     Dependency-free structural validation"
	@echo "  schema       Validate records against JSON Schemas"
	@echo "  determinism  Assert byte-identical clean rebuilds"
	@echo "  check        Full pipeline + tests + validation + determinism"

install:
	$(UV) sync --group dev

extract:
	$(UV) run python scripts/extract_srd.py --root .

manifest:
	$(UV) run python scripts/build_manifest.py --root .

bundle:
	$(UV) run python scripts/build_bundle.py --root .

llms-full:
	$(UV) run python scripts/build_llms_full.py --root .

search-index:
	$(UV) run python scripts/build_search_index.py --root .

collection-index:
	$(UV) run python scripts/build_collection_indexes.py --root .

coverage:
	$(UV) run python scripts/build_coverage.py --root .

review:
	$(UV) run python scripts/build_review_ledger.py --root .

review-stats:
	$(UV) run python scripts/manage_review_ledger.py --stats

vocab:
	$(UV) run python scripts/build_vocab.py --root .

sitemap:
	$(UV) run python scripts/build_sitemap.py --root .

test:
	$(UV) run python -m unittest discover -s tests -v

validate:
	$(UV) run python scripts/validate.py --root .

schema:
	$(UV) run python scripts/validate_schema.py --root .

determinism:
	$(UV) run python scripts/check_determinism.py

check: extract manifest bundle llms-full search-index collection-index coverage review vocab sitemap test validate schema determinism
