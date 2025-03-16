.PHONY: clean build test publish publish-test

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test:
	pytest tests/

build: clean
	python setup.py sdist bdist_wheel

publish-test: build
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

publish: build
	twine upload dist/*

version:
	@echo "Current version: $$(python setup.py --version)"

bump-version:
	@if [ "$(version)" = "" ]; then \
		echo "Usage: make bump-version version=X.Y.Z"; \
		exit 1; \
	fi
	sed -i '' "s/version=\".*\"/version=\"$(version)\"/" setup.py
	git add setup.py
	git commit -m "Bump version to $(version)"
	git tag -a v$(version) -m "Version $(version)"
	git push origin master
	git push origin v$(version)

install-dev:
	pip install -e ".[dev]"

install-deploy:
	pip install twine wheel setuptools --upgrade 