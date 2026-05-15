import os
from PIL import Image, ImageDraw, ImageFont

def create_spine(title, author, output_name):
    # --- 1. SETUP PATHS ---
    current_file_path = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file_path)
    project_root = os.path.dirname(backend_dir)
    font_path = os.path.join(backend_dir, "EBGaramond-Medium.ttf")
    output_path = os.path.join(project_root, 'frontend', 'assets', 'images', f"{output_name}_spine.jpg")

    # --- 2. CANVAS SETUP ---
    spine_color = (93, 64, 55) 
    width, height = 80, 400
    spine = Image.new('RGB', (width, height), color=spine_color)
    
    try:
        # Smaller font ensures it doesn't bleed off the 80px width
        font_title = ImageFont.truetype(font_path, 18)
        font_author = ImageFont.truetype(font_path, 14) # Author slightly smaller
    except:
        font_title = font_author = ImageFont.load_default()

    # --- 3. CREATE THE TITLE LAYER (Top) ---
    spaced_title = " ".join(list(title.upper()))
    # We create a layer just for the title
    title_layer = Image.new('RGBA', (300, 40), (0, 0, 0, 0))
    title_draw = ImageDraw.Draw(title_layer)
    title_draw.text((10, 5), spaced_title, font=font_title, fill="white")
    
    # Rotate and Paste Title at the TOP (y=20)
    title_vert = title_layer.rotate(270, expand=True)
    spine.paste(title_vert, (20, 20), title_vert)

    # --- 4. CREATE THE AUTHOR LAYER (Bottom) ---
    author_text = f"|  {author.upper()}"
    author_layer = Image.new('RGBA', (150, 40), (0, 0, 0, 0))
    author_draw = ImageDraw.Draw(author_layer)
    author_draw.text((10, 5), author_text, font=font_author, fill=(255, 255, 255, 200)) # Slightly faded
    
    # Rotate and Paste Author at the BOTTOM
    # We calculate the position: Height (400) - Author Length (~150) - Margin (20)
    author_vert = author_layer.rotate(270, expand=True)
    spine.paste(author_vert, (25, 230), author_vert)

    # --- 5. SAVE ---
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    spine.save(output_path)
    print(f"Successfully created: {output_path}")

if __name__ == "__main__":
    create_spine("The God of Small Things", "Arundhati Roy", "small_things")
    create_spine("The Great Gatsby", "F. Scott Fitzgerald", "gatsby")