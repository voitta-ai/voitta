from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="voitta",
    version="0.1.0",
    packages=find_packages(),
    install_requires=requirements,
    author="debedb",
    author_email="debedb@example.com",
    description="A library for routing API calls to different endpoints",
    keywords="api, routing, tools",
    url="https://github.com/debedb/voitta",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
