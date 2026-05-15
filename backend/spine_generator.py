import os
from PIL import Image, ImageDraw, ImageFont

def create_spine(title, author, output_name):
    # 1. SETUP PATHS FIRST (Defining them outside the try block)
    # This finds exactly where THIS file is saved
    current_file_path = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file_path)
    project_root = os.path.dirname(backend_dir)
    
    # Path to the font file
    font_path = os.path.join(backend_dir, "EBGaramond-Medium.ttf")
    
    # Path to the output image
    output_path = os.path.join(project_root, 'frontend', 'assets', 'images', f"{output_name}_spine.jpg")

    # 2. CREATE THE CANVAS
    spine_color = (93, 64, 55) 
    width, height = 80, 400
    spine = Image.new('RGB', (width, height), color=spine_color)
    
    # 3. LOAD THE FONT
    try:
        # We use a size of 28 for the elegant Garamond look
        font = ImageFont.truetype(font_path, 28)
    except Exception as e:
        print(f"Font Error: {e}. Python was looking for it at: {font_path}")
        print("Falling back to default font...")
        font = ImageFont.load_default()

    # 4. DRAW TEXT ON TEMPORARY LAYER
    # Adding spaces between letters in the title for a vintage feel
    spaced_title = " ".join(list(title.upper()))
    text_content = f"{spaced_title}   |   {author}"
    
    # Create a long transparent layer (600px) to prevent cutting off text
    text_layer = Image.new('RGBA', (600, 50), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text((20, 5), text_content, font=font, fill="white")

    # 5. ROTATION (Top-to-Bottom)
    vertical_text = text_layer.rotate(270, expand=True)

    # 6. PASTE ONTO SPINE
    spine.paste(vertical_text, (15, 25), vertical_text)

    # 7. SAVE TO ASSETS
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        spine.save(output_path)
        print(f"Successfully created: {output_path}")
    except Exception as e:
        print(f"Save Error: {e}")

if __name__ == "__main__":
    # Test cases
    create_spine("The God of Small Things", "Arundhati Roy", "small_things")
    create_spine("The Great Gatsby", "F. Scott Fitzgerald", "gatsby")