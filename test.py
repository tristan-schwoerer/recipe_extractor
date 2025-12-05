import os
from dotenv import load_dotenv
from custom_components.recipe_extractor.extractors import RecipeExtractor, fetch_recipe_text

# Load environment variables from .env file
load_dotenv()

# Fetch and extract a random recipe
text = fetch_recipe_text("https://www.madbanditten.dk/vikingegryde/")
extractor = RecipeExtractor(api_key=os.getenv("LANGEXTRACT_API_KEY"))
recipe = extractor.extract_recipe(text)

print(f"Title: {recipe.title}")
for ing in recipe.ingredients:
    print(f"  {ing.quantity} {ing.unit} {ing.name}")