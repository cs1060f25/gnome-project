SHELL := /bin/bash

# Setup
install:
	pip3 install --upgrade pip
	pip3 install --upgrade -r requirements.txt

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
