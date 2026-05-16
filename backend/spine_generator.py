import os
from PIL import Image, ImageDraw, ImageFont

def create_spine(title, author, output_name):
    current_file_path = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file_path)
    project_root = os.path.dirname(backend_dir)
    font_path = os.path.join(backend_dir, "EBGaramond-Medium.ttf")
    output_path = os.path.join(project_root, 'frontend', 'assets', 'images', f"{output_name}_spine.jpg")

    # 1. CANVAS SETUP (Direct Drawing Canvas)
    spine_color = (93, 64, 55) 
    width, height = 80, 400
    spine = Image.new('RGB', (width, height), color=spine_color)
    draw = ImageDraw.Draw(spine)
    
    try:
        font_title_size = 20  # Can start bigger since it wraps downward!
        font_author_size = 15
        font_title = ImageFont.truetype(font_path, font_title_size)
        font_author = ImageFont.truetype(font_path, font_author_size)
        print("Font loaded successfully.")
    except Exception as e:
        print(f"Error loading font: {e}. Using default font.")
        font_title = font_author = ImageFont.load_default()

    # 2. WRAP TITLE WORDS VERTICALLY
    # We slice the title into separate words so they stack neatly down the spine
    title_words = title.upper().split()
    
    y_offset = 30  # Initial padding from the top edge of the book
    line_spacing_title = 26  # Breathing room between words

    for word in title_words:
        # Calculate x_pos to perfectly center the word inside the 80px width
        word_width = draw.textlength(word, font=font_title)
        x_pos = (width - word_width) // 2
        
        # Draw the word directly on the spine
        draw.text((x_pos, y_offset), word, font=font_title, fill="white")
        y_offset += line_spacing_title

    # 3. ADD A SEPARATOR LINE
    # Draws a subtle decorative break right below the title
    y_offset += 15
    draw.line([(25, y_offset), (55, y_offset)], fill=(255, 255, 255, 100), width=1)
    y_offset += 25  # Space before the author starts

    # 4. RENDER AUTHOR BELOW THE TITLE
    author_words = author.upper().split()
    line_spacing_author = 20

    for word in author_words:
        word_width = draw.textlength(word, font=font_author)
        x_pos = (width - word_width) // 2
        
        # Draw author word with a slight 3D vintage transparency (alpha = 200)
        draw.text((x_pos, y_offset), word, font=font_author, fill=(255, 255, 255, 200))
        y_offset += line_spacing_author

    # 5. SAVE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    spine.save(output_path)
    print(f"Created: {output_name}_spine.jpg")
    print(f"Title: {title}, Author: {author}, Output Path: {output_path}")

if __name__ == "__main__":
    create_spine("The God of Small Things", "Arundhati Roy", "small_things")