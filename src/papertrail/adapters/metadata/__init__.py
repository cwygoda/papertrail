"""Metadata adapters."""

from .pikepdf import PikePdfAdapter
from .xmp import convert_yaml_to_xmp

__all__ = ["PikePdfAdapter", "convert_yaml_to_xmp"]
