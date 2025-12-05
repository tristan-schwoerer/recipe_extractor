"""Unit conversion utilities for recipe ingredients."""
from __future__ import annotations

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
    Convert imperial units to metric equivalents.
    
    Args:
        quantity: The numeric quantity
        unit: The unit string (e.g., 'cups', 'oz', 'lb', '°F')
        
    Returns:
        Tuple of (converted_quantity, metric_unit)
        If no conversion is needed, returns original values
        
    Examples:
        >>> convert_to_metric(1, 'cup')
        (240, 'ml')
        >>> convert_to_metric(1, 'lb')
        (454, 'g')
        >>> convert_to_metric(350, 'f')
        (177, '°C')
    """
    if not quantity or not unit:
        return quantity, unit
    
    unit_lower = unit.lower().strip()
    
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
