# Voitta

Voitta is a Python library for routing API calls to different endpoints, with support for various tools and functions.

## Features

- Route API calls to different endpoints
- Support for various tools and functions
- Canvas functionality for interactive applications
- Asynchronous API calls
- Support for authentication tokens

## Installation

You can install the package directly from GitHub:

```bash
pip install git+https://github.com/debedb/voitta.git
```

Or clone the repository and install locally:

```bash
git clone https://github.com/debedb/voitta.git
cd voitta
pip install -e .
```

## Usage

Here's a simple example of how to use Voitta:

```python
from voitta import VoittaRouter

# Define endpoints
endpoints = [
    ("api1", {"url": "https://api1.example.com", "description": "API 1"}),
    ("api2", {"url": "https://api2.example.com", "description": "API 2"}),
    ("canvas", {"url": "canvas"})
]

# Create router
router = VoittaRouter(endpoints)

# Get available tools
tools = router.get_tools()

# Get prompt for tools
prompt = router.get_prompt()

# Call a function
import asyncio

async def main():
    result = await router.call_function("1____some_function", {"param": "value"}, token=None, oauth_token=None)
    print(result)

asyncio.run(main())
```

## Requirements

- Python 3.8+
- Dependencies listed in requirements.txt

## License

MIT
