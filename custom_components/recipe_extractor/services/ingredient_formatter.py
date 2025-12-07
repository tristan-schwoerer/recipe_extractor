"""
Ingredient Formatter and Unit Converter.

This module handles formatting, scaling, and conversion of recipe ingredients
for display in todo lists. Includes unit conversion utilities for imperial to
metric conversions and multi-language unit normalization.
"""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Unit normalizations - spoon measurements to standard English abbreviations
SPOON_TO_STANDARD = {
    # German teaspoons
    "tl": ("tsp", 1),
    "teelöffel": ("tsp", 1),
    # German tablespoons
    "el": ("tbsp", 1),
    "esslöffel": ("tbsp", 1),
    # Danish teaspoons
    "tsk": ("tsp", 1),
    # Danish tablespoons
    "spsk": ("tbsp", 1),
    # Swedish/Norwegian tablespoons
    "msk": ("tbsp", 1),
    # Pinch equivalents (knife tip)
    "knsp": ("pinch", 1),  # Danish knivspids
    "messerspitze": ("pinch", 1),  # German knife tip
}

# Volume conversions to milliliters (ml)
VOLUME_TO_ML = {
    # Imperial/US
    "cup": 240,
    "cups": 240,
    "c": 240,
    "tablespoon": 15,
    "tablespoons": 15,
    "tbsp": 15,
    "tbs": 15,
    "tb": 15,
    "teaspoon": 5,
    "teaspoons": 5,
    "tsp": 5,
    "fluid ounce": 30,
    "fluid ounces": 30,
    "fl oz": 30,
    "fl. oz": 30,
    "floz": 30,
    "pint": 473,
    "pints": 473,
    "pt": 473,
    "quart": 946,
    "quarts": 946,
    "qt": 946,
    "gallon": 3785,
    "gallons": 3785,
    "gal": 3785,
    # Metric (normalized)
    "milliliter": 1,
    "milliliters": 1,
    "ml": 1,
    "liter": 1000,
    "liters": 1000,
    "l": 1000,
    "dl": 100,
    "deciliter": 100,
    "deciliters": 100,
}

# Weight conversions to grams (g)
WEIGHT_TO_G = {
    # Imperial/US
    "ounce": 28.35,
    "ounces": 28.35,
    "oz": 28.35,
    "pound": 453.592,
    "pounds": 453.592,
    "lb": 453.592,
    "lbs": 453.592,
    # Metric (normalized)
    "gram": 1,
    "grams": 1,
    "g": 1,
    "kilogram": 1000,
    "kilograms": 1000,
    "kg": 1000,
}

# Temperature conversions
TEMPERATURE_UNITS = {
    "fahrenheit": "f",
    "f": "f",
    "°f": "f",
    "celsius": "c",
    "c": "c",
    "°c": "c",
}


def convert_to_metric(quantity: float, unit: str) -> tuple[float | int, str]:
    """
    Convert imperial units to metric equivalents and normalize spoon measurements.

    Args:
        quantity: The numeric quantity
        unit: The unit string (e.g., 'cups', 'oz', 'lb', '°F', 'TL', 'EL')

    Returns:
        Tuple of (converted_quantity, metric_unit)

    Examples:
        >>> convert_to_metric(1, 'cup')
        (240, 'ml')
        >>> convert_to_metric(1, 'lb')
        (454, 'g')
        >>> convert_to_metric(1, 'TL')
        (1, 'tsp')
        >>> convert_to_metric(2, 'EL')
        (2, 'tbsp')
    """
    if not quantity or not unit:
        return quantity, unit

    unit_lower = unit.lower().strip()

    # First, normalize spoon measurements to standard English abbreviations
    if unit_lower in SPOON_TO_STANDARD:
        standard_unit, multiplier = SPOON_TO_STANDARD[unit_lower]
        return quantity * multiplier, standard_unit

    # Keep standard English spoon measurements as-is (don't convert to ml)
    if unit_lower in ["tsp", "teaspoon", "teaspoons", "tbsp", "tablespoon", "tablespoons", "pinch", "dash"]:
        return quantity, unit

    # Volume conversions
    if unit_lower in VOLUME_TO_ML:
        ml = quantity * VOLUME_TO_ML[unit_lower]

        # Use liters for large volumes
        if ml >= 1000:
            return round(ml / 1000, 2), "l"
        else:
            return round(ml, 0), "ml"

    # Weight conversions
    if unit_lower in WEIGHT_TO_G:
        grams = quantity * WEIGHT_TO_G[unit_lower]

        # Use kilograms for large weights
        if grams >= 1000:
            return round(grams / 1000, 2), "kg"
        else:
            return round(grams, 0), "g"

    # Temperature conversions
    if unit_lower in TEMPERATURE_UNITS:
        temp_type = TEMPERATURE_UNITS[unit_lower]
        if temp_type == "f":
            celsius = (quantity - 32) * 5 / 9
            return round(celsius, 0), "°C"

    # Return original if no conversion needed
    return quantity, unit


def format_quantity(quantity: float | int | None) -> str:
    """
    Format quantity to remove unnecessary decimals.

    Args:
        quantity: The numeric quantity (can be int, float, or None)

    Returns:
        Formatted string (empty string if quantity is None)

    Examples:
        >>> format_quantity(2.0)
        '2'
        >>> format_quantity(2.5)
        '2.5'
        >>> format_quantity(2.125)
        '2.13'
    """
    if quantity is None:
        return ""

    # If it's a whole number, return without decimals
    if quantity == int(quantity):
        return str(int(quantity))

    # Otherwise, return with up to 2 decimal places, removing trailing zeros
    return f"{quantity:.2f}".rstrip('0').rstrip('.')


_LOGGER = logging.getLogger(__name__)


def scale_ingredients(
    ingredients: list[dict[str, Any]],
    original_servings: int | float | None,
    target_servings: int | float
) -> list[dict[str, Any]]:
    """Scale ingredient quantities based on servings.

    Args:
        ingredients: List of ingredient dicts with name, quantity, unit
        original_servings: Original number of servings in the recipe
        target_servings: Target number of servings to scale to (can be fractional)

    Returns:
        List of scaled ingredient dicts
    """
    if original_servings is None or original_servings <= 0:
        _LOGGER.warning(
            "Cannot scale recipe: original servings not available or invalid")
        return ingredients

    if target_servings <= 0:
        _LOGGER.warning(
            "Cannot scale recipe: target servings must be positive")
        return ingredients

    scaling_factor = target_servings / original_servings
    _LOGGER.info("Scaling ingredients from %d to %d servings (factor: %.2f)",
                 original_servings, target_servings, scaling_factor)

    scaled_ingredients = []
    for ingredient in ingredients:
        scaled_ingredient = ingredient.copy()
        if ingredient.get('quantity') is not None:
            original_qty = ingredient['quantity']
            scaled_qty = original_qty * scaling_factor
            scaled_ingredient['quantity'] = scaled_qty
            _LOGGER.debug("Scaled %s: %.2f -> %.2f",
                          ingredient.get('name'), original_qty, scaled_qty)
        scaled_ingredients.append(scaled_ingredient)

    return scaled_ingredients


def format_ingredients_for_todo(
    ingredients: list[dict[str, Any]],
    convert_units: bool
) -> list[str]:
    """Format ingredients as strings for todo list.

    Args:
        ingredients: List of ingredient dicts with name, quantity, unit
        convert_units: Whether to convert imperial units to metric

    Returns:
        List of formatted ingredient strings
    """
    todo_items = []

    for idx, ingredient in enumerate(ingredients):
        parts = []
        quantity = ingredient.get('quantity')
        unit = ingredient.get('unit')
        name = ingredient.get('name')

        _LOGGER.debug("Formatting ingredient %d: name='%s', quantity='%s', unit='%s'",
                      idx + 1, name, quantity, unit)

        # Skip invalid values
        if not name or name in ('null', 'None', None):
            _LOGGER.debug(
                "Skipping ingredient %d: invalid or missing name", idx + 1)
            continue

        # Clean null-like values
        if quantity in ('null', 'None', None):
            quantity = None
        if unit in ('null', 'None', None):
            unit = None

        # Convert units if enabled
        if convert_units and quantity is not None and unit:
            try:
                original_qty = quantity
                original_unit = unit
                quantity, unit = convert_to_metric(float(quantity), unit)
                _LOGGER.debug("Converted units for %s: %s %s -> %s %s",
                              name, original_qty, original_unit, quantity, unit)
            except (ValueError, TypeError) as e:
                _LOGGER.debug("Failed to convert units for %s: %s", name, e)
                # Keep original if conversion fails

        # Build ingredient string
        parts.append(str(name))

        if quantity is not None:
            formatted_qty = format_quantity(quantity)
            if formatted_qty:
                parts.append(formatted_qty)

        if unit:
            parts.append(str(unit))

        formatted_item = ' '.join(parts)
        _LOGGER.debug("Formatted ingredient %d as: '%s'",
                      idx + 1, formatted_item)
        todo_items.append(formatted_item)

    return todo_items
