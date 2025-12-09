"""
JSON-LD Recipe Parser.

This module handles parsing of structured recipe data from JSON-LD format,
supporting multiple ingredient formats (English, German, Danish, Swedish).
"""
from __future__ import annotations

import re
import logging
from ..models.recipe import Recipe, Ingredient
from .base_parser import BaseRecipeParser

_LOGGER = logging.getLogger(__name__)


class JSONLDRecipeParser(BaseRecipeParser):
    """Parses recipe data from structured JSON-LD format.

    This parser handles pre-structured recipe data that follows the Schema.org
    Recipe format, requiring no AI inference.
    """

    def __init__(self) -> None:
        """Initialize the JSON-LD recipe parser."""
        _LOGGER.debug("Initialized JSONLDRecipeParser")

    def _parse_fraction(self, fraction_str: str) -> float:
        """Safely parse a fraction string like '1/2' or '3/4'.

        Args:
            fraction_str: A string containing a fraction (e.g., '1/2', '3/4')

        Returns:
            The decimal value of the fraction

        Raises:
            ValueError: If the fraction string is invalid
            ZeroDivisionError: If denominator is zero
        """
        if '/' not in fraction_str:
            return float(fraction_str)

        parts = fraction_str.strip().split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid fraction format: {fraction_str}")

        numerator = float(parts[0].strip())
        denominator = float(parts[1].strip())

        if denominator == 0:
            raise ZeroDivisionError(
                f"Fraction has zero denominator: {fraction_str}")

        return numerator / denominator

    def _apply_unicode_fractions(self, text: str) -> str:
        """Replace unicode fraction characters with decimal equivalents.

        Handles both standalone fractions (½) and mixed numbers (2½).
        Mixed numbers are converted by adding the decimal: 2½ -> 2 + 0.5 = 2.5

        Args:
            text: String potentially containing unicode fractions

        Returns:
            String with unicode fractions replaced by decimals
        """
        import re

        # Map unicode fractions to their decimal values
        fraction_values = {
            '½': 0.5,
            '⅓': 0.333,
            '⅔': 0.667,
            '¼': 0.25,
            '¾': 0.75,
            '⅛': 0.125,
            '⅜': 0.375,
            '⅝': 0.625,
            '⅞': 0.875
        }

        # Handle mixed numbers (e.g., "2½" -> "2.5")
        for fraction_char, decimal_value in fraction_values.items():
            # Pattern to match number followed by fraction (e.g., "2½")
            pattern = rf'(\d+){re.escape(fraction_char)}'

            def replace_mixed(match):
                whole_number = int(match.group(1))
                return str(whole_number + decimal_value)

            text = re.sub(pattern, replace_mixed, text)

            # Also handle standalone fractions
            text = text.replace(fraction_char, str(decimal_value))

        return text

    def _parse_quantity_string(self, quantity_str: str) -> float | None:
        """Parse a quantity string that may contain fractions.

        Args:
            quantity_str: String like '2', '1/2', '2 1/2', '2.5'

        Returns:
            Parsed float value or None if parsing fails
        """
        try:
            # Handle fractions
            if '/' in quantity_str:
                parts = quantity_str.split()
                return sum(self._parse_fraction(p) for p in parts)
            else:
                return float(self._apply_unicode_fractions(quantity_str))
        except (ValueError, TypeError, ZeroDivisionError) as e:
            _LOGGER.debug(f"Failed to parse quantity '{quantity_str}': {e}")
            return None

    def _parse_ingredient(self, ingredient_text: str) -> Ingredient:
        """Parse a JSON-LD ingredient string into structured Ingredient.

        Supports multiple formats:
        - Compact: "250g flour"
        - Standard English: "1 cup butter, softened"
        - German/Danish: "TL Salz 0.5"
        - Name-quantity: "Große Zwiebel(n) 1"
        - Quantity-name: "1 große Zwiebel"

        Args:
            ingredient_text: Raw ingredient string

        Returns:
            Structured Ingredient object
        """
        # Common unit abbreviations and full names (English + German/Danish/Swedish)
        units = r'(?:cups?|tablespoons?|tbsp?|teaspoons?|tsp?|ounces?|oz|pounds?|lbs?|grams?|g|kilograms?|kg|milliliters?|ml|liters?|l|pinch|dash|clove|piece|slice|tl|el|teelöffel|esslöffel|messerspitze|tsk|spsk|knsp|msk|dl)'

        # Try pattern 1a: "quantityunit name" compact format (e.g., "250g flour")
        pattern1a = rf'^([\d./½⅓⅔¼¾⅛⅜⅝⅞]+)({units})\b\s+(.+)$'
        match = re.match(pattern1a, ingredient_text.strip(), re.IGNORECASE)

        if match:
            quantity_str, unit, name = match.groups()
            quantity = self._parse_quantity_string(quantity_str)

            return Ingredient(
                name=name.strip(),
                quantity=quantity,
                unit=unit.strip() if unit else None
            )

        # Try pattern 1b: "quantity unit name" (English format: "1 cup butter")
        # Use word boundary \b after unit to prevent matching "g" in "große"
        pattern1b = rf'^([\d./½⅓⅔¼¾⅛⅜⅝⅞]+(?:\s+[\d./½⅓⅔¼¾⅛⅜⅝⅞]+)?)\s+({units})\b\s+(.+)$'
        match = re.match(pattern1b, ingredient_text.strip(), re.IGNORECASE)

        if match:
            quantity_str, unit, name = match.groups()
            quantity = self._parse_quantity_string(quantity_str)

            return Ingredient(
                name=name.strip(),
                quantity=quantity,
                unit=unit.strip() if unit else None
            )

        # Try pattern 2: "unit name quantity" (German/Danish format: "TL Korianderpulver 0.5")
        pattern2 = rf'^({units})\b\s+(.+?)\s+([\d./½⅓⅔¼¾⅛⅜⅝⅞]+(?:\s+[\d./½⅓⅔¼¾⅛⅜⅝⅞]+)?)$'
        match = re.match(pattern2, ingredient_text.strip(), re.IGNORECASE)

        if match:
            unit, name, quantity_str = match.groups()
            quantity = self._parse_quantity_string(quantity_str)

            return Ingredient(
                name=name.strip(),
                quantity=quantity,
                unit=unit.strip() if unit else None
            )

        # Try pattern 3: "name quantity" without unit (e.g., "Große Zwiebel(n) 1")
        pattern3 = rf'^(.+?)\s+([\d./½⅓⅔¼¾⅛⅜⅝⅞]+(?:\s+[\d./½⅓⅔¼¾⅛⅜⅝⅞]+)?)$'
        match = re.match(pattern3, ingredient_text.strip(), re.IGNORECASE)

        if match:
            name, quantity_str = match.groups()
            quantity = self._parse_quantity_string(quantity_str)

            return Ingredient(
                name=name.strip(),
                quantity=quantity,
                unit=None
            )

        # Try pattern 4: "quantity name" without unit (e.g., "1 große Zwiebel", "2 eggs")
        pattern4 = rf'^([\d./½⅓⅔¼¾⅛⅜⅝⅞]+(?:\s+[\d./½⅓⅔¼¾⅛⅜⅝⅞]+)?)\s+(.+)$'
        match = re.match(pattern4, ingredient_text.strip(), re.IGNORECASE)

        if match:
            quantity_str, name = match.groups()
            quantity = self._parse_quantity_string(quantity_str)

            return Ingredient(
                name=name.strip(),
                quantity=quantity,
                unit=None
            )

        # No pattern matched, just return the text as name
        return Ingredient(name=ingredient_text.strip(), quantity=None, unit=None)

    def parse_recipe(self, text: str) -> Recipe | None:
        """Parse JSON-LD structured recipe text directly without AI.

        Args:
            text: The structured text from JSON-LD extraction

        Returns:
            Recipe object, or None if parsing fails
        """
        if not text or len(text.strip()) < 10:
            _LOGGER.warning("Text too short for JSON-LD parsing")
            return None

        lines = text.split('\n')
        title = ""
        servings = None
        ingredients = []

        in_ingredients = False

        for line in lines:
            line = line.strip()
            if line.startswith("Recipe: "):
                title = line[8:]  # Remove "Recipe: " prefix
            elif line.startswith("Servings: "):
                servings_text = line[10:]  # Remove "Servings: " prefix
                # Extract number from strings like "48", "Makes 10", "6 servings"
                match = re.search(r'\d+', servings_text)
                if match:
                    servings = int(match.group())
            elif line == "Ingredients:":
                in_ingredients = True
            elif in_ingredients and line.startswith("- "):
                ingredient_text = line[2:]  # Remove "- " prefix
                ingredients.append(self._parse_ingredient(ingredient_text))

        if not title:
            _LOGGER.warning("No title found in JSON-LD data")
            return None

        return Recipe(title=title, servings=servings, ingredients=ingredients)
