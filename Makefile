.PHONY: clean build publish publish-test publish-test-alt publish-test-debug check-version check-git-status check-master-branch test bump-patch bump-minor bump-major install ensure-deps

VERSION_FILE := setup.py
CURRENT_VERSION := $(shell grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/")

clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/ voitta/__pycache__/

# Ensure required packages are installed
ensure-deps:
	pip install -U setuptools wheel twine

build: clean ensure-deps
	python setup.py sdist bdist_wheel

bump-version: bump-minor
	@NEW_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/") && \
	echo "New version: $$NEW_VERSION"

# Publish to PyPI
# Requires:
# 1. PyPI credentials to be configured in ~/.pypirc or via TWINE_USERNAME and TWINE_PASSWORD environment variables
# 2. GITHUB_TOKEN environment variable for GitHub authentication
# 3. Clean working directory (no uncommitted changes)
# 4. Being on the master branch
publish: check-git-status check-master-branch build
	@echo "Fetching latest version from PyPI..."
	@LATEST_PYPI_VERSION=$$(curl -s https://pypi.org/pypi/voitta/json | grep -o '"version":"[^"]*"' | head -1 | sed 's/"version":"//;s/"//') && \
	if [ -z "$$LATEST_PYPI_VERSION" ]; then \
		echo "Could not fetch latest version from PyPI. Using version from setup.py."; \
		LATEST_PYPI_VERSION="0.0.0"; \
	fi && \
	echo "Latest version on PyPI: $$LATEST_PYPI_VERSION" && \
	CURRENT_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/") && \
	echo "Current version in setup.py: $$CURRENT_VERSION" && \
	if [ "$$CURRENT_VERSION" = "$$LATEST_PYPI_VERSION" ]; then \
		echo "Version in setup.py matches PyPI version. Incrementing..." && \
		python -c "import re; \
			version='$$CURRENT_VERSION'; \
			parts=version.split('.'); \
			parts[-1]=str(int(parts[-1])+1); \
			new_version='.'.join(parts); \
			print(f'New version: {new_version}'); \
			with open('$(VERSION_FILE)', 'r') as f: content = f.read(); \
			with open('$(VERSION_FILE)', 'w') as f: f.write(re.sub(r\"VERSION = '[^']*'\", f\"VERSION = '{new_version}'\", content))"; \
		CURRENT_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/"); \
	fi && \
	echo "Publishing version $$CURRENT_VERSION to PyPI..." && \
	git add $(VERSION_FILE) && \
	git commit -m "Bump version to $$CURRENT_VERSION" && \
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

# Publish to TestPyPI for testing before publishing to the main PyPI repository
# Note: This requires the 'testpypi' section to be properly configured in ~/.pypirc
# Based on your current ~/.pypirc, you need to update it to:
#   [distutils]
#   index-servers =
#     pypi
#     testpypi
#     voitta
#
#   [testpypi]
#   repository = https://test.pypi.org/legacy/
#   username = __token__
#   password = pypi-YOUR_TESTPYPI_TOKEN_HERE
publish-test: check-git-status check-master-branch check-version build
	@NEW_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/") && \
	twine upload --repository testpypi dist/* && \
	echo "Published version $$NEW_VERSION to TestPyPI"

# Alternative publish to TestPyPI that doesn't require testpypi section in ~/.pypirc
# You can authenticate using environment variables:
#   export TWINE_USERNAME=__token__
#   export TWINE_PASSWORD=pypi-YOUR_TESTPYPI_TOKEN_HERE
# 
# If you get a 403 Forbidden error, it could be due to:
# 1. Authentication issues - make sure your token is correct and has the right permissions
# 2. The package version already exists on TestPyPI - increment the version in setup.py
publish-test-alt: check-git-status check-master-branch check-version build
	@NEW_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/") && \
	twine upload --verbose --repository-url https://test.pypi.org/legacy/ dist/* && \
	echo "Published version $$NEW_VERSION to TestPyPI"

# Publish to TestPyPI with debug information
publish-test-debug: check-git-status check-master-branch check-version build
	@NEW_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/") && \
	TWINE_USERNAME=__token__ TWINE_PASSWORD=$$(read -p "Enter your TestPyPI token: " token && echo $$token) \
	twine upload --verbose --repository-url https://test.pypi.org/legacy/ dist/* && \
	echo "Published version $$NEW_VERSION to TestPyPI"

# Check if the current version already exists on TestPyPI
check-version:
	@NEW_VERSION=$$(grep -o "VERSION = '[^']*'" $(VERSION_FILE) | sed "s/VERSION = '\(.*\)'/\1/") && \
	echo "Checking if version $$NEW_VERSION exists on TestPyPI..." && \
	if curl -s https://test.pypi.org/pypi/voitta/$$NEW_VERSION/json > /dev/null; then \
		echo "Version $$NEW_VERSION already exists on TestPyPI. Please increment the version in setup.py."; \
		exit 1; \
	else \
		echo "Version $$NEW_VERSION does not exist on TestPyPI. You can proceed with publishing."; \
	fi

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
