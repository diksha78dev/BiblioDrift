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
        # We use a size of 20 for the elegant Garamond look
        font = ImageFont.truetype(font_path, 20)
    except Exception as e:
        print(f"Font Error: {e}. Python was looking for it at: {font_path}")
        print("Falling back to default font...")
        font = ImageFont.load_default()

# --- STEP 4: DRAW TEXT ON A MUCH LONGER LAYER ---
    spaced_title = " ".join(list(title.upper()))
    text_content = f"{spaced_title}   |   {author.upper()}"
    
    # We make the width 800 so it can hold the whole string
    text_layer = Image.new('RGBA', (800, 50), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    
    # Calculate text length to center it vertically later
    text_len = text_draw.textlength(text_content, font=font)
    
    # Draw the text
    text_draw.text((10, 5), text_content, font=font, fill="white")

    # --- STEP 5: ROTATION ---
    vertical_text = text_layer.rotate(270, expand=True)

    # --- STEP 6: DYNAMIC CENTERING ---
    # We want the text to start near the top but stay centered horizontally (x=25)
    # y=20 puts it near the top of the book
    spine.paste(vertical_text, (25, 20), vertical_text)

    # 7. SAVE TO ASSETS
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        spine.save(output_path)
        print(f"Successfully created: {output_path}")
    except Exception as e:
        print(f"Save Error: {e}")

if __name__ == "__main__":
    # Test cases only for me to check if this works 
    create_spine("The God of Small Things", "Arundhati Roy", "small_things")
    create_spine("The Great Gatsby", "F. Scott Fitzgerald", "gatsby")