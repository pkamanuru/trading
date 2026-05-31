PYTHON := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: venv install run test clean

venv:
	python3 -m virtualenv .venv

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) main.py

test:
	$(PYTHON) -m unittest tests/test_scaffold.py

clean:
	rm -rf .venv
