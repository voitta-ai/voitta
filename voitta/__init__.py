"""
Voitta - A library for routing API calls to different endpoints.

This package provides functionality for routing API calls to different endpoints,
with support for various tools and functions.
"""

from .router import VoittaRouter
from .canvas import CanvasDescription

__version__ = "0.1.0"
__all__ = ["VoittaRouter", "CanvasDescription"]
