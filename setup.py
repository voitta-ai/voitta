from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="voitta",
    version="0.1.0",
    author="Gregory Demin",
    author_email="debedb@gmail.com",
    description="A Python library for routing API calls to different endpoints",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/debedb/voitta",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.68.0",
        "pydantic>=1.8.0",
        "httpx>=0.23.0",
        "PyJWT>=2.3.0",
        "pandas>=1.3.0",
        "requests>=2.26.0",
        "python-dotenv>=0.19.0",
        "dspy-ai>=2.0.0",
        "jsonpath-ng>=1.5.0",
        "pyyaml>=6.0",
        "asgiref>=3.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.910",
            "twine>=4.0.0",
            "wheel>=0.37.0",
            "build>=0.7.0",
        ],
    },
)
