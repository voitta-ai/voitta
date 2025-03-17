# Voitta

[![PyPI version](https://img.shields.io/pypi/v/voitta.svg)](https://pypi.org/project/voitta/)
[![Python Versions](https://img.shields.io/pypi/pyversions/voitta.svg)](https://pypi.org/project/voitta/)
[![Downloads](https://static.pepy.tech/badge/voitta/month)](https://pepy.tech/project/voitta)
[![License](https://img.shields.io/github/license/voitta-ai/voitta)](https://github.com/voitta-ai/voitta/blob/main/LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/voitta-ai/voitta.svg)](https://github.com/voitta-ai/voitta/stargazers)

<!-- These badges will appear on both GitHub and PyPI pages since this README is used as the long description for PyPI -->

A Python framework for routing, automating, and orchestrating LLM tool calls. Voitta simplifies the integration of AI agents with external tools and APIs, enabling more powerful and flexible AI applications.

## Features

- **Tool Call Routing**: Seamlessly route LLM tool calls to the appropriate handlers
- **Flexible Configuration**: Define your tools and routing logic using YAML or Python
- **Framework Agnostic**: Works with any LLM provider or framework
- **Extensible Architecture**: Easily add custom tools and integrations
- **Observability**: Monitor and debug tool calls with built-in logging

## Installation

### From PyPI (Stable Release)

```bash
pip install voitta
```

### From TestPyPI (Pre-release Versions)

To install the latest pre-release version from TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ voitta
```

The `--extra-index-url` flag is needed to fetch dependencies from the main PyPI repository, as TestPyPI may not have all the required dependencies.

You can also specify a particular version:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ voitta==0.2.3
```

Note: Pre-release versions on TestPyPI may contain experimental features and bugs. Use in production environments at your own risk.

## Quick Start

```python
from voitta import Voitta

# Initialize Voitta
voitta = Voitta()

# Register a tool handler
@voitta.tool("get_weather")
def get_weather(location, unit="celsius"):
    # Implementation to fetch weather data
    return {"temperature": 22, "condition": "sunny", "location": location, "unit": unit}

# Process an LLM tool call
result = voitta.process_tool_call({
    "name": "get_weather",
    "arguments": {"location": "San Francisco", "unit": "fahrenheit"}
})

print(result)  # Output: {"temperature": 72, "condition": "sunny", "location": "San Francisco", "unit": "fahrenheit"}
```

## Usage

For detailed usage examples and documentation, please refer to:
- [Voitta Example Repository](https://github.com/voitta-ai/voitta-example)
- [Voitta Official Website](https://voitta.com)
- [Voitta on PyPI](https://pypi.org/project/voitta/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
