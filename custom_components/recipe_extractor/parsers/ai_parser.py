"""
AI-based Recipe Parser using LangExtract.

This module handles AI-powered extraction of recipe data from unstructured text
using Google's LangExtract library with Gemini models.
"""
from __future__ import annotations

import logging

import langextract as lx
from langextract import tokenizer

from ..models.recipe import Recipe, Ingredient
from .base_parser import BaseRecipeParser
from .ai_prompts import EXTRACTION_PROMPT
from .ai_examples import RECIPE_EXAMPLES

_LOGGER = logging.getLogger(__name__)


class AIRecipeParser(BaseRecipeParser):
    """Parses recipe data from unstructured text using AI (LangExtract)."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        """Initialize the AI recipe parser.

        Args:
            api_key: API key for the language model
            model: The model to use for extraction

        Raises:
            ValueError: If API key is empty
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        self.api_key = api_key
        self.model = model
        # Use UnicodeTokenizer for multi-language support (fixes alignment warnings)
        self.tokenizer = tokenizer.UnicodeTokenizer()
        _LOGGER.debug("Initialized AIRecipeParser with model %s", model)

    def parse_recipe(self, text: str) -> Recipe | None:
        """Parse recipe information from unstructured text using AI.

        Args:
            text: The raw recipe text

        Returns:
            A Recipe object with extracted information, or None if extraction fails
        """
        if not text or len(text.strip()) < 100:
            _LOGGER.warning(
                "Text too short for extraction: %d characters", len(text) if text else 0)
            return None

        _LOGGER.info(
            "Parsing recipe from %d characters of text using AI", len(text))

        try:
            _LOGGER.debug("Calling LangExtract with model %s", self.model)
            result = lx.extract(
                text_or_documents=text,
                prompt_description=EXTRACTION_PROMPT,
                model_id=self.model,
                examples=RECIPE_EXAMPLES,
                tokenizer=self.tokenizer,  # Use UnicodeTokenizer for multi-language support
                api_key=self.api_key
            )

            if result and hasattr(result, 'extractions') and result.extractions:
                # Extract individual title, servings, and ingredient entities with attributes
                title = None
                servings = None
                ingredients = []

                for extraction in result.extractions:
                    if extraction.extraction_class == "title":
                        title = extraction.extraction_text

                    elif extraction.extraction_class == "servings":
                        # Parse servings - can be string or None
                        servings_str = extraction.extraction_text
                        if servings_str is not None:
                            try:
                                servings = int(servings_str)
                            except (ValueError, TypeError):
                                servings = None

                    elif extraction.extraction_class == "ingredient":
                        # Get attributes from the extraction
                        attrs = extraction.attributes or {}
                        name = attrs.get('name', extraction.extraction_text)

                        # Parse quantity - can be string or None
                        quantity_str = attrs.get('quantity')
                        quantity = None
                        if quantity_str is not None:
                            try:
                                quantity = float(quantity_str)
                            except (ValueError, TypeError):
                                quantity = None

                        unit = attrs.get('unit')
                        group = attrs.get('group')

                        ingredient = Ingredient(
                            name=name,
                            quantity=quantity,
                            unit=unit,
                            group=group
                        )
                        ingredients.append(ingredient)

                # Create recipe if we have title and ingredients
                if title and ingredients:
                    _LOGGER.info("Successfully parsed recipe '%s' with %d ingredients using AI (servings: %s)",
                                 title, len(ingredients), servings)
                    recipe = Recipe(
                        title=title,
                        servings=servings,
                        ingredients=ingredients
                    )
                    return recipe

                if not title:
                    _LOGGER.warning("AI parsing completed but no title found")
                if not ingredients:
                    _LOGGER.warning(
                        "AI parsing completed but no ingredients found")

                return None

            _LOGGER.warning("No extractions found in LangExtract result")
            return None

        except Exception as e:
            _LOGGER.error("Error during AI recipe parsing: %s",
                          str(e), exc_info=True)
            raise
