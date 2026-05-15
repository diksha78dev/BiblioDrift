import os
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
        # Slightly smaller title font (16px) to ensure fit
        font_title = ImageFont.truetype(font_path, 16)
        font_author = ImageFont.truetype(font_path, 14)
    except:
        font_title = font_author = ImageFont.load_default()

    # 2. RENDER THE TITLE
    spaced_title = " ".join(list(title.upper()))
    # We use a very long canvas to measure it properly
    title_canvas = Image.new('RGBA', (800, 50), (0, 0, 0, 0))
    t_draw = ImageDraw.Draw(title_canvas)
    
    # Measure title length
    t_width = t_draw.textlength(spaced_title, font=font_title)
    t_draw.text((0, 5), spaced_title, font=font_title, fill="white")
    
    # Rotate and Paste Title at the very top
    title_vert = title_canvas.rotate(270, expand=True)
    spine.paste(title_vert, (22, 20), title_vert)

    # 3. RENDER THE AUTHOR (DYNAMICALLY)
    # We start the author 40px AFTER the title ends OR at 250px, whichever is lower
    # This prevents the "collision" you saw
    title_end_y = 20 + t_width 
    author_start_y = max(title_end_y + 40, 250)

    author_text = f"|  {author.upper()}"
    author_canvas = Image.new('RGBA', (200, 50), (0, 0, 0, 0))
    a_draw = ImageDraw.Draw(author_canvas)
    a_draw.text((0, 5), author_text, font=font_author, fill=(255, 255, 255, 200))
    
    author_vert = author_canvas.rotate(270, expand=True)
    
    # Ensure author doesn't fall off the bottom of the book (400px)
    if author_start_y < 380:
        spine.paste(author_vert, (26, int(author_start_y)), author_vert)

    # 4. SAVE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    spine.save(output_path)
    print(f"Created: {output_name}_spine.jpg")

if __name__ == "__main__":
    create_spine("The God of Small Things", "Arundhati Roy", "small_things")