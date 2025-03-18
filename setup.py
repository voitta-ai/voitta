from setuptools import setup, find_packages
import re

# Version scheme based on existing PyPI versions
# Last version on PyPI is 0.0.1.8, so we'll increment from there
VERSION = '0.5.0'

setup(
    name='voitta',
    version=VERSION,
    packages=find_packages(),
    author='Voitta',
    author_email='support@voitta.ai',
    description='A Python framework for LLM tool calls routing, automation, and orchestration',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/voitta-ai/voitta',
    project_urls={
        'Documentation': 'https://voitta.com',
        'Examples': 'https://github.com/voitta-ai/voitta-example',
        'Bug Reports': 'https://github.com/voitta-ai/voitta/issues',
        'Source Code': 'https://github.com/voitta-ai/voitta',
        'Website': 'https://voitta.ai',
        'Changelog': 'https://github.com/voitta-ai/voitta/blob/master/CHANGELOG.md',
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
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
