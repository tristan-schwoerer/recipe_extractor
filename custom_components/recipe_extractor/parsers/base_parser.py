"""
Base Recipe Parser.

This module defines the base interface that all recipe parsers must implement.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from ..models.recipe import Recipe


class BaseRecipeParser(ABC):
    """Abstract base class for recipe parsers.

    All recipe parsers must implement the parse_recipe method to convert
    raw text into structured Recipe objects.
    """

    @abstractmethod
    def parse_recipe(self, text: str) -> Recipe | None:
        """Parse recipe information from text.

        Args:
            text: The raw recipe text to parse

        Returns:
            A Recipe object with extracted information, or None if parsing fails
        """
        pass
