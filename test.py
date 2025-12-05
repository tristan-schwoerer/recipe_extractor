import os
from dotenv import load_dotenv
from custom_components.recipe_extractor.extractors import RecipeExtractor, fetch_recipe_text

# Load environment variables from .env file
load_dotenv()

# Fetch and extract
text = fetch_recipe_text("https://www.chefkoch.de/rezepte/1169621223051653/Brillas-Bauernfruehstueck-vegetarisch.html")
extractor = RecipeExtractor(api_key=os.getenv("LANGEXTRACT_API_KEY"))
recipe = extractor.extract_recipe(text)

print(f"Title: {recipe.title}")
for ing in recipe.ingredients:
    print(f"  {ing.quantity} {ing.unit} {ing.name}")