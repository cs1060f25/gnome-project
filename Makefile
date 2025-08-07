SHELL := /bin/bash
.PHONY: install demo clean

install:
	pip3 install --upgrade pip
	pip3 install --upgrade -r requirements.txt

demo:
	source .env && python3 demo/app.py

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
