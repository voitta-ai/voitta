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
        "fastapi",
        "pydantic",
        "httpx",
        "PyJWT",
        "pandas",
        "requests",
        "python-dotenv",
        "dspy-ai",
        "jsonpath-ng",
        "pyyaml",
        "asgiref",
    ],
)
