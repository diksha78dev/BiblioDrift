#logic/flow of the code is: spine that flips text 90 degrees from top-to-bottom
#creating a blank canvas which is a tall thin rec spine
# write text on a transparent layer 
# we write the title and author horizontally first because python's text tools work best that way.
# then lastly we rotate the layer: by 27 degrees now 
# paste & save: we put that vertical text onto our colored spine
from PIL import Image, ImageDraw, ImageFont
import os
def create_spine(title, author, output_name):
    # 1. SETTINGS: Defining a "Cozy" Brown and Spine Size
    spine_color = (93, 64, 55) # A warm bookstore brown like as if the books are bound in brown paper
    width, height = 80, 400    # tall and narrow
    
    # 2. CREATING THE CANVAS
    spine = Image.new('RGB', (width, height), color=spine_color)
    
    # 3. LOAD FONT i have chosen eb garamond for the antique bookstore feel
    try:
        # We tell it to look inside the backend folder for the specific Medium font
        font_path = os.path.join(backend_dir, "EBGaramond-Medium.ttf") 
        font = ImageFont.truetype(font_path, 28)
    except Exception as e:
        print(f"Font error: {e}. Looking in {font_path}")
        font = ImageFont.load_default()

    # 4. DRAW TEXT ON TEMPORARY LAYER
    # To make it look vintage, we space out the letters in the Title
    spaced_title = " ".join(list(title.upper()))
    text_content = f"{spaced_title}   |   {author}"
    # Create a transparent layer for the text (horizontal first)
    # We make it long enough to fit the full title and author
    text_layer = Image.new('RGBA', (600, 50), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    # We draw the text. (20, 5) gives it a small margin
    text_draw.text((20, 5), text_content, font=font, fill="white")

    # 5. THE ROTATION MAGIC
    # Rotate by 270 degrees to make it read Top-to-Bottom
    vertical_text = text_layer.rotate(270, expand=True)

    # 6. PASTE ONTO MAIN SPINE
    # We center the text horizontally on the spine
    spine.paste(vertical_text, (15, 25), vertical_text) #(15, 25) offsets the text from the top and left edges

    # 7. SAVE TO ASSETS
    # We save it in the frontend assets so the website can see it
    output_path = os.path.join('../frontend/assets/images', f"{output_name}_spine.jpg")
    os.makedirs(os.path.dirname(output_path), exist_ok=True) # Ensure the directory exists
    spine.save(output_path)
    print(f"Successfully created: {output_path}")

# --- TEST IT ---
# Running this will create a file in your assets folder!
if __name__ == "__main__":
    # Test with a classic Indian Author since that's your focus!
    create_spine("The God of Small Things", "Arundhati Roy", "small_things")
    # And your test case
    create_spine("The Great Gatsby", "F. Scott Fitzgerald", "gatsby")