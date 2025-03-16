from setuptools import setup, find_packages
import re

# Use a simpler version scheme
VERSION = '1.0.1'

setup(
    name='voitta',
    version=VERSION,
    packages=find_packages(),
    author='Voitta',
    author_email='support@voitta.ai',
    description='LLM tool calls routing and automation',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://voitta.ai',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        "pyyaml",
        "fastapi",
        "jsonpath_ng",
        "httpx",
        "dspy",
        "pydantic",
        "dotenv",
        "asgiref",
        "uuid",
        "pyjwt"
    ]
)

# typing
# jwt
