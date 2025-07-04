SHELL := /bin/bash

# Setup
install:
	pip3 install --upgrade pip
	pip3 install --upgrade -r requirements.txt

# Unit tests
unit-test-all: unit-test-app unit-test-embed unit-test-gdrive unit-test-parse unit-test-db

unit-test-app:
	PYTHONPATH=$(CURDIR):$(CURDIR)/.. pytest test_suite/unit_tests/test_api.py

unit-test-embed:
	PYTHONPATH=$(CURDIR):$(CURDIR)/.. pytest test_suite/unit_tests/test_embed.py

unit-test-gdrive:
	PYTHONPATH=$(CURDIR):$(CURDIR)/.. pytest test_suite/unit_tests/test_gdrive.py

unit-test-parse:
	PYTHONPATH=$(CURDIR):$(CURDIR)/.. pytest test_suite/unit_tests/test_parse.py

unit-test-db:
	PYTHONPATH=$(CURDIR):$(CURDIR)/.. pytest test_suite/unit_tests/test_db.py

# System tests
test-local:
	source .env && python3 -m test_suite.system_tests.local_search

test-token:
	bash test_suite/system_tests/test_store_user_token.txt

test-upload:
	bash test_suite/system_tests/test_file_upload.txt

test-search:
	bash test_suite/system_tests/test_file_search.txt

get-token:
	python3 google_drive_helpers/quickstart.py

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} +
