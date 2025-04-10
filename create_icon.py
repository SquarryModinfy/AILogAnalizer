from PIL import Image, ImageDraw
import os

def create_icon():
    # Создаем изображение 256x256 пикселей
    size = 256
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Рисуем круг
    margin = 20
    draw.ellipse([margin, margin, size-margin, size-margin], 
                 fill=(41, 128, 185),  # Синий цвет
                 outline=(255, 255, 255),  # Белая обводка
                 width=10)
    
    # Рисуем букву "L" (для Log)
    draw.text((size//2-30, size//2-30), 
              "L", 
              fill=(255, 255, 255),  # Белый цвет
              font=None, 
              font_size=100)
    
    # Сохраняем как .ico для Windows
    image.save('icon.ico', format='ICO')
    
    # Для Linux создаем .icns
    if os.name != 'nt':  # Если не Windows
        # Создаем временные PNG файлы разных размеров
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        for s in sizes:
            resized = image.resize((s, s), Image.Resampling.LANCZOS)
            resized.save(f'icon_{s}x{s}.png')
        
        # Создаем .icns файл (требуется iconutil на macOS)
        if os.system('which iconutil >/dev/null 2>&1') == 0:
            os.system('mkdir icon.iconset')
            for s in sizes:
                os.system(f'cp icon_{s}x{s}.png icon.iconset/icon_{s}x{s}.png')
                if s <= 512:
                    os.system(f'cp icon_{s}x{s}.png icon.iconset/icon_{s//2}x{s//2}@2x.png')
            os.system('iconutil -c icns icon.iconset')
            os.system('rm -rf icon.iconset')
        
        # Удаляем временные файлы
        for s in sizes:
            os.remove(f'icon_{s}x{s}.png')

if __name__ == "__main__":
    create_icon()
    print("Иконки созданы успешно!") 