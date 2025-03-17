.PHONY: clean build publish publish-test check-git-status check-master-branch test install ensure-deps

VERSION_FILE := setup.py
CURRENT_VERSION := $(shell grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/")

clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/ voitta/__pycache__/

# Ensure required packages are installed
ensure-deps:
	pip install -U setuptools wheel twine

build: clean ensure-deps
	python setup.py sdist bdist_wheel

# Bump the patch/revision version (0.2.0 -> 0.2.1)
bump-revision:
	@echo "Current version: $(CURRENT_VERSION)"
	@python -c "import re; \
		version='$(CURRENT_VERSION)'; \
		parts=version.split('.'); \
		parts[2]=str(int(parts[2])+1); \
		new_version='.'.join(parts); \
		print(f'Bumping revision to: {new_version}'); \
		with open('$(VERSION_FILE)', 'r') as f: content = f.read(); \
		with open('$(VERSION_FILE)', 'w') as f: f.write(re.sub(r\"VERSION = '[^']*'\", f\"VERSION = '{new_version}'\", content))"

# Bump the minor version and reset patch (0.2.1 -> 0.3.0)
bump-minor:
	@echo "Current version: $(CURRENT_VERSION)"
	@python -c "import re; \
		version='$(CURRENT_VERSION)'; \
		parts=version.split('.'); \
		parts[1]=str(int(parts[1])+1); \
		parts[2]='0'; \
		new_version='.'.join(parts); \
		print(f'Bumping minor version to: {new_version}'); \
		with open('$(VERSION_FILE)', 'r') as f: content = f.read(); \
		with open('$(VERSION_FILE)', 'w') as f: f.write(re.sub(r\"VERSION = '[^']*'\", f\"VERSION = '{new_version}'\", content))"

# Check if there are uncommitted changes
check-git-status:
	@echo "Checking for uncommitted changes..."
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: There are uncommitted changes in the repository."; \
		echo "Please commit or stash your changes before publishing."; \
		exit 1; \
	else \
		echo "Git working directory is clean."; \
	fi

# Check if we're on the master branch
check-master-branch:
	@echo "Checking current branch..."
	@CURRENT_BRANCH=$$(git rev-parse --abbrev-ref HEAD) && \
	if [ "$$CURRENT_BRANCH" != "master" ]; then \
		echo "Error: Not on master branch. Current branch: $$CURRENT_BRANCH"; \
		echo "Please switch to the master branch before publishing."; \
		exit 1; \
	else \
		echo "On master branch."; \
	fi

# Publish to TestPyPI - bumps revision number
publish-test: check-git-status check-master-branch bump-revision build
	@CURRENT_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/") && \
	echo "Publishing version $$CURRENT_VERSION to TestPyPI..." && \
	git add $(VERSION_FILE) && \
	git commit -m "Bump revision to $$CURRENT_VERSION for TestPyPI" && \
	git tag -a v$$CURRENT_VERSION -m "Release v$$CURRENT_VERSION to TestPyPI" && \
	GITHUB_PUSH_URL="https://$${GITHUB_TOKEN}@github.com/voitta-ai/voitta.git" && \
	if [ -n "$${GITHUB_TOKEN}" ]; then \
		git push "$${GITHUB_PUSH_URL}" master && \
		git push "$${GITHUB_PUSH_URL}" v$$CURRENT_VERSION; \
	else \
		git push origin master && \
		git push origin v$$CURRENT_VERSION; \
	fi && \
	twine upload --repository testpypi dist/* && \
	echo "Published version $$CURRENT_VERSION to TestPyPI and created git tag v$$CURRENT_VERSION"

# Publish to PyPI - bumps minor version
publish: check-git-status check-master-branch bump-minor build
	@CURRENT_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/") && \
	echo "Publishing version $$CURRENT_VERSION to PyPI..." && \
	git add $(VERSION_FILE) && \
	git commit -m "Bump version to $$CURRENT_VERSION for PyPI release" && \
	git tag -a v$$CURRENT_VERSION -m "Release v$$CURRENT_VERSION" && \
	GITHUB_PUSH_URL="https://$${GITHUB_TOKEN}@github.com/voitta-ai/voitta.git" && \
	if [ -n "$${GITHUB_TOKEN}" ]; then \
		git push "$${GITHUB_PUSH_URL}" master && \
		git push "$${GITHUB_PUSH_URL}" v$$CURRENT_VERSION; \
	else \
		git push origin master && \
		git push origin v$$CURRENT_VERSION; \
	fi && \
	twine upload dist/* && \
	echo "Published version $$CURRENT_VERSION to PyPI and created git tag v$$CURRENT_VERSION"

test:
	pytest

install: clean
	pip install -e .
