from custom_components.recipe_extractor.extractors import RecipeExtractor, fetch_recipe_text

# Fetch and extract
text = fetch_recipe_text("https://www.chefkoch.de/rezepte/1169621223051653/Brillas-Bauernfruehstueck-vegetarisch.html")
extractor = RecipeExtractor(api_key="AIzaSyBlFizT4E8We0GDkQAi3V77uhe_904R0P8")
recipe = extractor.extract_recipe(text)

print(f"Title: {recipe.title}")
for ing in recipe.ingredients:
    print(f"  {ing.quantity} {ing.unit} {ing.name}")