"""
Example recipes for training the LangExtract model.
"""
from langextract.data import ExampleData, Extraction


RECIPE_EXAMPLES = [
    ExampleData(
        text="""
Chocolate Chip Cookies

Ingredients:
- 2 1/4 cups all-purpose flour
- 1 tsp baking soda
- 1 tsp salt
- 1 cup butter, softened
- 3/4 cup granulated sugar
- 2 large eggs
- 2 cups chocolate chips
- Powdered Sugar
- Baking paper
""",
        extractions=[
            Extraction(
                extraction_class="title",
                extraction_text="Chocolate Chip Cookies"
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="2 1/4 cups all-purpose flour",
                attributes={"name": "all-purpose flour", "quantity": "2.25", "unit": "cups", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="1 tsp baking soda",
                attributes={"name": "baking soda", "quantity": "1.0", "unit": "tsp", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="1 tsp salt",
                attributes={"name": "salt", "quantity": "1.0", "unit": "tsp", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="1 cup butter, softened",
                attributes={"name": "butter, softened", "quantity": "1.0", "unit": "cup", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="3/4 cup granulated sugar",
                attributes={"name": "granulated sugar", "quantity": "0.75", "unit": "cup", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="2 large eggs",
                attributes={"name": "eggs", "quantity": "2.0", "unit": "large", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="2 cups chocolate chips",
                attributes={"name": "chocolate chips", "quantity": "2.0", "unit": "cups", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="Powdered Sugar",
                attributes={"name": "Powdered Sugar", "quantity": None, "unit": None, "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="Baking paper",
                attributes={"name": "Baking paper", "quantity": None, "unit": None, "group": None}
            )
        ]
    ),
    
    ExampleData(
        text="""
Gewürzkuchen

Zutaten:
- 4 Ei(er)
- 300 g Zucker
- 350 g Mehl
- 1 Pck. Backpulver
- 250 ml Olivenöl
- 1 TL, gehäuft Salz
- 2 Paprikaschote(n), rote
- Petersilie
- Salz und Pfeffer
- Oregano
""",
        extractions=[
            Extraction(
                extraction_class="title",
                extraction_text="Gewürzkuchen"
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="4 Ei(er)",
                attributes={"name": "Ei(er)", "quantity": "4.0", "unit": None, "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="300 g Zucker",
                attributes={"name": "Zucker", "quantity": "300.0", "unit": "g", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="350 g Mehl",
                attributes={"name": "Mehl", "quantity": "350.0", "unit": "g", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="1 Pck. Backpulver",
                attributes={"name": "Backpulver", "quantity": "1.0", "unit": "Pck.", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="250 ml Olivenöl",
                attributes={"name": "Olivenöl", "quantity": "250.0", "unit": "ml", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="1 TL, gehäuft Salz",
                attributes={"name": "Salz, gehäuft", "quantity": "1.0", "unit": "TL", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="2 Paprikaschote(n), rote",
                attributes={"name": "Paprikaschote(n), rote", "quantity": "2.0", "unit": None, "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="Petersilie",
                attributes={"name": "Petersilie", "quantity": None, "unit": None, "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="Salz und Pfeffer",
                attributes={"name": "Salz und Pfeffer", "quantity": None, "unit": None, "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="Oregano",
                attributes={"name": "Oregano", "quantity": None, "unit": None, "group": None}
            )
        ]
    ),
    
    ExampleData(
        text="""
Recipe: Pizza Dough

Ingredients:

For the dough:
  - 500g Flour
  - 300ml Water, lukewarm
  - 1TL Salt
  - 7g Yeast

For the topping:
  - 200g Tomato sauce
  - 300g Mozzarella
  - Basil
  - Olive oil
""",
        extractions=[
            Extraction(
                extraction_class="title",
                extraction_text="Pizza Dough"
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="500g Flour",
                attributes={"name": "Flour", "quantity": "500.0", "unit": "g", "group": "For the dough"}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="300ml Water, lukewarm",
                attributes={"name": "Water, lukewarm", "quantity": "300.0", "unit": "ml", "group": "For the dough"}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="1TL Salt",
                attributes={"name": "Salt", "quantity": "1.0", "unit": "TL", "group": "For the dough"}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="7g Yeast",
                attributes={"name": "Yeast", "quantity": "7.0", "unit": "g", "group": "For the dough"}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="200g Tomato sauce",
                attributes={"name": "Tomato sauce", "quantity": "200.0", "unit": "g", "group": "For the topping"}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="300g Mozzarella",
                attributes={"name": "Mozzarella", "quantity": "300.0", "unit": "g", "group": "For the topping"}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="Basil",
                attributes={"name": "Basil", "quantity": None, "unit": None, "group": "For the topping"}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="Olive oil",
                attributes={"name": "Olive oil", "quantity": None, "unit": None, "group": "For the topping"}
            )
        ]
    ),
    
    ExampleData(
        text="""
Recipe: Beef Stew

Ingredients:
- 1.5kg/ 3.3lb beef chuck, cubed
- 500ml/ 2 cups beef broth
- 3 tbsp/ 45g butter
- 2 large onions
- Salt and pepper

For serving:
- Fresh parsley
""",
        extractions=[
            Extraction(
                extraction_class="title",
                extraction_text="Beef Stew"
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="1.5kg/ 3.3lb beef chuck, cubed",
                attributes={"name": "beef chuck, cubed", "quantity": "1.5", "unit": "kg", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="500ml/ 2 cups beef broth",
                attributes={"name": "beef broth", "quantity": "500.0", "unit": "ml", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="3 tbsp/ 45g butter",
                attributes={"name": "butter", "quantity": "3.0", "unit": "tbsp", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="2 large onions",
                attributes={"name": "onions", "quantity": "2.0", "unit": "large", "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="Salt and pepper",
                attributes={"name": "Salt and pepper", "quantity": None, "unit": None, "group": None}
            ),
            Extraction(
                extraction_class="ingredient",
                extraction_text="Fresh parsley",
                attributes={"name": "Fresh parsley", "quantity": None, "unit": None, "group": "For serving"}
            )
        ]
    )
]
