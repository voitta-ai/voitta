.PHONY: clean build publish test bump-patch bump-minor bump-major install

VERSION_FILE := setup.py
CURRENT_VERSION := $(shell grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/")

clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/ voitta/__pycache__/

build: clean
	python setup.py sdist bdist_wheel

bump-version: bump-minor
	@NEW_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/") && \
	echo "New version: $$NEW_VERSION"

publish: build bump-version
	@NEW_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/") && \
	git tag -a v$$NEW_VERSION -m "Release v$$NEW_VERSION" && \
	git push origin v$$NEW_VERSION && \
	twine upload dist/* && \
	echo "Published version $$NEW_VERSION to PyPI and created git tag v$$NEW_VERSION"

test:
	pytest

install: clean
	pip install -e .


bump-minor:
	@echo "Current version: $(CURRENT_VERSION)"
	@NEW_VERSION=$$(python -c "import re; \
		version='$(CURRENT_VERSION)'; \
		parts=version.split('.'); \
		parts[1]=str(int(parts[1])+1); \
		parts[2]='0'; \
		print('.'.join(parts))") && \
	sed -i.bak "s/VERSION = '$(CURRENT_VERSION)'/VERSION = '$$NEW_VERSION'/" $(VERSION_FILE) && \
	rm -f $(VERSION_FILE).bak && \
	echo "Bumped version to: $$NEW_VERSION"
