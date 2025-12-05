"""
Recipe data models for the Recipe Extractor integration.

This module defines the Pydantic models used to structure recipe data
extracted from unstructured text using LangExtract.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    """A structured representation of a single ingredient.
    
    Attributes:
        name: The name of the ingredient (e.g., 'all-purpose flour', 'Mehl')
        quantity: Optional numeric quantity (e.g., 2.5, 250)
        unit: Optional unit of measurement (e.g., 'cups', 'g', 'TL')
        group: Optional ingredient group/section (e.g., 'For the dough')
    """
    
    name: str = Field(
        description="The name of the ingredient, e.g., 'all-purpose flour'"
    )
    quantity: float | None = Field(
        default=None,
        description="The numeric quantity, e.g., 2.5"
    )
    unit: str | None = Field(
        default=None,
        description="The unit of measurement, e.g., 'cups', 'grams', 'tbsp'"
    )
    group: str | None = Field(
        default=None,
        description="The ingredient group or section, e.g., 'For the dough', 'Für den Boden'"
    )


class Recipe(BaseModel):
    """The top-level schema for the entire recipe.
    
    Attributes:
        title: The recipe title/name
        ingredients: List of structured ingredients with quantities and units
    """
    
    title: str = Field(
        description="The title of the recipe"
    )
    ingredients: list[Ingredient] = Field(
        description="A list of all ingredients, structured using the Ingredient model"
    )
