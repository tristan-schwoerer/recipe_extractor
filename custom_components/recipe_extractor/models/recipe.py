"""
Recipe data models for the Recipe Extractor integration.

This module defines the Pydantic models used to structure recipe data
extracted from unstructured text using LangExtract.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    """A structured representation of a single ingredient."""
    
    name: str = Field(
        description="The name of the ingredient, e.g., 'all-purpose flour'"
    )
    quantity: Optional[float] = Field(
        default=None,
        description="The numeric quantity, e.g., 2.5"
    )
    unit: Optional[str] = Field(
        default=None,
        description="The unit of measurement, e.g., 'cups', 'grams', 'tbsp'"
    )
    group: Optional[str] = Field(
        default=None,
        description="The ingredient group or section, e.g., 'For the dough', 'Für den Boden'"
    )


class Recipe(BaseModel):
    """The top-level schema for the entire recipe."""
    
    title: str = Field(
        description="The title of the recipe"
    )
    ingredients: List[Ingredient] = Field(
        description="A list of all ingredients, structured using the Ingredient model"
    )
