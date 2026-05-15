import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

def create_spine(title, author, output_name):
    current_file_path = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file_path)
    project_root = os.path.dirname(backend_dir)
    font_path = os.path.join(backend_dir, "EBGaramond-Medium.ttf")
    output_path = os.path.join(project_root, 'frontend', 'assets', 'images', f"{output_name}_spine.jpg")

    # 1. CANVAS SETUP
    spine_color = (93, 64, 55) 
    width, height = 80, 400
    spine = Image.new('RGB', (width, height), color=spine_color)
    
    try:
        # Smaller font (18px) allows for more "stacking" room
        font = ImageFont.truetype(font_path, 18)
    except:
        font = ImageFont.load_default()

    # 2. THE STACKING LOGIC
    # We will split the title if it's longer than 20 characters
    spaced_title = " ".join(list(title.upper()))
    title_lines = textwrap.wrap(spaced_title, width=25) # Breaks long titles
    
    # 3. DRAWING THE PIECES
    # We create a temporary layer for the WHOLE vertical stack
    # Imagine a long horizontal strip that we will rotate
    temp_canvas_width = 380 
    temp_canvas = Image.new('RGBA', (temp_canvas_width, 60), (0, 0, 0, 0))
    draw = ImageDraw.Draw(temp_canvas)

    # Position 1: The Title (Starts at the left of our temp canvas)
    title_text = "  ".join(title_lines) 
    draw.text((10, 5), title_text, font=font, fill="white")

    # Position 2: The Author (We push this to the far right of the temp canvas)
    author_text = f"|  {author.upper()}"
    author_len = draw.textlength(author_text, font=font)
    draw.text((temp_canvas_width - author_len - 10, 5), author_text, font=font, fill="rgba(255,255,255,180)")

    # 4. ROTATION & PASTE
    # This flips our "Title --------- Author" strip into a "Title (Top) / Author (Bottom)" vertical strip
    vertical_stack = temp_canvas.rotate(270, expand=True)
    
    # Paste it onto the spine, centered horizontally
    # (width of spine - width of text) // 2 = centered
    spine.paste(vertical_stack, (15, 10), vertical_stack)

    # 5. SAVE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    spine.save(output_path)
    print(f"Successfully created stacked spine: {output_path}")

if __name__ == "__main__":
    create_spine("The God of Small Things", "Arundhati Roy", "small_things")
    create_spine("The Great Gatsby", "F. Scott Fitzgerald", "gatsby")