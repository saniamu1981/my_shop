from PIL import Image, ImageDraw, ImageFont
import os

def make_icon(size, path, bg='#212529', fg='#ffffff', letter='M'):
    img = Image.new('RGB', (size, size), bg)
    draw = ImageDraw.Draw(img)

    # Пробуем шрифт Arial
    try:
        font = ImageFont.truetype("arial.ttf", size=int(size * 0.6))
    except Exception:
        font = ImageFont.load_default()

    # Центрируем букву
    bbox = draw.textbbox((0, 0), letter, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) / 2 - bbox[0]
    y = (size - text_height) / 2 - bbox[1]

    draw.text((x, y), letter, fill=fg, font=font)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    print(f'Создано: {path} ({size}x{size})')


if __name__ == '__main__':
    make_icon(192, 'static/icons/icon-192x192.png')
    make_icon(512, 'static/icons/icon-512x512.png')
    make_icon(180, 'static/icons/icon-180x180.png')
    make_icon(32,  'static/icons/favicon-32x32.png')