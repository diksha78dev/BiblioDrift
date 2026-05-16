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
        font_title_size = 16
        font_author_size = 14
        font_title = ImageFont.truetype(font_path, font_title_size)
        font_author = ImageFont.truetype(font_path, font_author_size)
        print("Font loaded successfully.")
    except Exception as e:
        print(f"Error loading font: {e}. Using default font.")
        font_title = font_author = ImageFont.load_default()

    # 2. RENDER THE TITLE
    title_canvas = Image.new('RGBA', (400, 400), (0, 0, 0, 0))  # Increased height to ensure full title fits
    t_draw = ImageDraw.Draw(title_canvas)

    # Wrap title to fit within the spine width
    max_lines = 4
    max_width = 70
    while True:
        words = title.upper().split()
        wrapped_title = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if t_draw.textlength(test_line, font=font_title) > max_width:  # Adjust width limit as needed
                wrapped_title.append(current_line)
                current_line = word
            else:
                current_line = test_line
        wrapped_title.append(current_line)

        if len(wrapped_title) <= max_lines:
            break
        font_title_size -= 1
        font_title = ImageFont.truetype(font_path, font_title_size)

    # Draw wrapped title
    y_offset = 0
    for line in wrapped_title:
        t_draw.text((0, y_offset), line, font=font_title, fill="white")
        y_offset += font_title_size + 4  # Line spacing

    # Rotate and Paste Title
    title_vert = title_canvas.rotate(270, expand=True)
    title_height = title_vert.size[1]
    title_y_position = max(20, (height - title_height) // 2)  # Center the title vertically
    spine.paste(title_vert, (22, 20), title_vert)

    # 3. RENDER THE AUTHOR
    author_canvas = Image.new('RGBA', (400, 400), (0, 0, 0, 0))  # Adjusted canvas size for author
    a_draw = ImageDraw.Draw(author_canvas)

    # Dynamically adjust font size for author
    while a_draw.textlength(author.upper(), font=font_author) > max_width:
        font_author_size -= 1
        font_author = ImageFont.truetype(font_path, font_author_size)

    a_draw.text((0, 0), author.upper(), font=font_author, fill=(255, 255, 255, 200))

    author_vert = author_canvas.rotate(270, expand=True)

    # Place author below the title, ensuring a new line
    author_start_y = y_offset + 40  # Add spacing after the title
    if author_start_y + author_vert.size[1] <= height:
        spine.paste(author_vert, (26, int(author_start_y)), author_vert)

    # 4. SAVE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    spine.save(output_path)
    print(f"Created: {output_name}_spine.jpg")
    print(f"Title: {title}, Author: {author}, Output Path: {output_path}")

if __name__ == "__main__":
    create_spine("The God of Small Things", "Arundhati Roy", "small_things")