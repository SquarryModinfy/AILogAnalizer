"""
Стили для интерфейса приложения
"""

# Основной стиль приложения
MAIN_STYLE = """
QMainWindow {
    background-color: #f0f0f0;
}
QWidget {
    background-color: #ffffff;
}
QPushButton {
    background-color: #4CAF50;
    color: white;
    padding: 10px;
    border: none;
    border-radius: 5px;
    font-size: 16px;
}
QPushButton:hover {
    background-color: #45a049;
}
QTextEdit {
    background-color: #ffffff;
    color: #333333;
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 5px;
    selection-background-color: #4CAF50;
    selection-color: white;
}
QTextEdit::placeholder {
    color: #999999;
}
QProgressBar {
    background-color: #f0f0f0;
    text-align: center;
    padding: 2px;
    border: 1px solid #ccc;
    border-radius: 5px;
}
QProgressBar::chunk {
    background-color: #4CAF50;
    width: 20px;
}
QLabel {
    font-size: 16px;
    font-weight: bold;
}
"""

# Стиль для статусной строки
STATUS_BAR_STYLE = """
QStatusBar {
    background-color: #f0f0f0;
    color: #333333;
    padding: 5px;
    font-size: 12px;
}
"""

# Стиль для окна загрузки
LOADING_WINDOW_STYLE = """
QDialog {
    background-color: #ffffff;
}
QLabel {
    font-size: 14px;
    color: #333333;
}
QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 3px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #4CAF50;
}
"""

# Стиль для окна настроек
SETTINGS_WINDOW_STYLE = """
QDialog {
    background-color: #ffffff;
}
QLabel {
    font-size: 14px;
    color: #333333;
}
QLineEdit {
    padding: 5px;
    border: 1px solid #cccccc;
    border-radius: 3px;
    font-size: 14px;
    background-color: #ffffff;
    color: #333333;
}
QLineEdit:focus {
    border: 1px solid #4CAF50;
}
QTextEdit {
    padding: 5px;
    border: 1px solid #cccccc;
    border-radius: 3px;
    font-size: 13px;
    font-family: Consolas, Monaco, monospace;
    background-color: #fafafa;
    color: #333333;
}
QTextEdit:focus {
    border: 1px solid #4CAF50;
}
QPushButton {
    background-color: #4CAF50;
    color: white;
    padding: 8px 15px;
    border: none;
    border-radius: 3px;
    font-size: 14px;
}
QPushButton:hover {
    background-color: #45a049;
}
QGroupBox {
    font-size: 14px;
    font-weight: bold;
    border: 1px solid #cccccc;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
}
""" 