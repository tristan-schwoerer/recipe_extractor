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
            try:
                quantity = float(quantity_str.replace('½', '0.5').replace('⅓', '0.333')
                                 .replace('⅔', '0.667').replace('¼', '0.25')
                                 .replace('¾', '0.75'))
            except:
                quantity = None

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
            try:
                # Handle fractions
                if '/' in quantity_str:
                    parts = quantity_str.split()
                    quantity = sum(eval(p) for p in parts)
                else:
                    quantity = float(quantity_str.replace('½', '0.5').replace('⅓', '0.333')
                                     .replace('⅔', '0.667').replace('¼', '0.25')
                                     .replace('¾', '0.75'))
            except:
                quantity = None

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
            try:
                # Handle fractions
                if '/' in quantity_str:
                    parts = quantity_str.split()
                    quantity = sum(eval(p) for p in parts)
                else:
                    quantity = float(quantity_str.replace('½', '0.5').replace('⅓', '0.333')
                                     .replace('⅔', '0.667').replace('¼', '0.25')
                                     .replace('¾', '0.75'))
            except:
                quantity = None

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
            try:
                # Handle fractions
                if '/' in quantity_str:
                    parts = quantity_str.split()
                    quantity = sum(eval(p) for p in parts)
                else:
                    quantity = float(quantity_str.replace('½', '0.5').replace('⅓', '0.333')
                                     .replace('⅔', '0.667').replace('¼', '0.25')
                                     .replace('¾', '0.75'))
            except:
                quantity = None

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
            try:
                # Handle fractions
                if '/' in quantity_str:
                    parts = quantity_str.split()
                    quantity = sum(eval(p) for p in parts)
                else:
                    quantity = float(quantity_str.replace('½', '0.5').replace('⅓', '0.333')
                                     .replace('⅔', '0.667').replace('¼', '0.25')
                                     .replace('¾', '0.75'))
            except:
                quantity = None

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
