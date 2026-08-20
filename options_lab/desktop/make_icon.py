import os
from PIL import Image, ImageDraw

def create_icon():
    img = Image.new('RGBA', (32, 32), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw indigo circle with white dollar/chart line
    draw.ellipse((2, 2, 30, 30), fill=(64, 81, 181, 255))
    draw.line([(8, 20), (14, 14), (20, 18), (26, 10)], fill=(255, 255, 255, 255), width=2)
    
    desktop_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(desktop_dir, 'tray_icon.png')
    img.save(icon_path, 'PNG')
    print("Created tray icon at:", icon_path)

if __name__ == '__main__':
    create_icon()
