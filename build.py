import os
import sys
import shutil
from PyInstaller.__main__ import run

def build_app():
    # Remove previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    icon = 'icon.ico' if sys.platform == 'win32' else 'icon.icns'
    params = [
        'main.py',
        '--name=AILogAnalyzer',
        '--onefile',
        '--windowed',
        '--clean',
        '--add-data=.env;.',
        f'--icon={icon}',
        '--hidden-import=torch',
        '--hidden-import=transformers',
        '--hidden-import=faiss',
        '--hidden-import=numpy',
        '--hidden-import=PySide6',
        '--hidden-import=requests',
        '--hidden-import=python-dotenv',
        '--hidden-import=tqdm',
    ]
    if sys.platform == 'win32':
        params.extend([
            '--hidden-import=win32api',
            '--hidden-import=win32con',
        ])
    run(params)
    print("Build complete!")
    print("Executable is located in the 'dist' folder")

if __name__ == "__main__":
    build_app()