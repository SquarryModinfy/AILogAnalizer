import os
import sys
import shutil
from PyInstaller.__main__ import run

def build_app():
    # Очищаем предыдущие сборки
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Определяем иконку в зависимости от ОС
    icon = 'icon.ico' if sys.platform == 'win32' else 'icon.icns'
    
    # Базовые параметры для PyInstaller
    params = [
        'main.py',  # Основной файл
        '--name=AILogAnalyzer',  # Имя выходного файла
        '--onefile',  # Создать один исполняемый файл
        '--windowed',  # Не показывать консоль
        '--clean',  # Очистить временные файлы
        '--add-data=.env;.',  # Добавить файл .env
        f'--icon={icon}',  # Иконка приложения
        '--hidden-import=torch',
        '--hidden-import=transformers',
        '--hidden-import=faiss',
        '--hidden-import=numpy',
        '--hidden-import=PySide6',
        '--hidden-import=requests',
        '--hidden-import=python-dotenv',
        '--hidden-import=tqdm',
    ]
    
    # Добавляем специфичные для ОС параметры
    if sys.platform == 'win32':
        params.extend([
            '--hidden-import=win32api',
            '--hidden-import=win32con',
        ])
    
    # Запускаем сборку
    run(params)
    
    print("Сборка завершена!")
    print(f"Исполняемый файл находится в папке 'dist'")

if __name__ == "__main__":
    build_app() 