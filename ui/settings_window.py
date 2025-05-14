"""
Окно настроек приложения
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QTextEdit, QGroupBox)
from PySide6.QtCore import Qt
from ui.styles import SETTINGS_WINDOW_STYLE
import os
from core.prompts import DEFAULT_LOG_ANALYSIS_PROMPT
from core.constants import logger

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Группа настроек API
        api_group = QGroupBox("Настройки API")
        api_layout = QVBoxLayout(api_group)
        
        url_layout = QHBoxLayout()
        url_label = QLabel("URL LLM сервера:")
        self.url_input = QLineEdit()
        self.url_input.setText(parent.api_url)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        api_layout.addLayout(url_layout)
        
        key_layout = QHBoxLayout()
        key_label = QLabel("API Key:")
        self.key_input = QLineEdit()
        self.key_input.setText(parent.api_key)
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        api_layout.addLayout(key_layout)
        
        layout.addWidget(api_group)
        
        # Группа настроек промпта
        prompt_group = QGroupBox("Настройка промпта")
        prompt_layout = QVBoxLayout(prompt_group)
        
        prompt_label = QLabel("Промпт для анализа:")
        prompt_layout.addWidget(prompt_label)
        
        self.prompt_input = QTextEdit()
        self.prompt_input.setMinimumHeight(200)  # Минимум 10 строк
        
        # Загружаем текущий промпт из .env или используем стандартный
        current_prompt = os.getenv('LLM_PROMPT', DEFAULT_LOG_ANALYSIS_PROMPT)
        self.prompt_input.setText(current_prompt)
        
        prompt_layout.addWidget(self.prompt_input)
        
        # Кнопка восстановления стандартного промпта
        self.reset_prompt_btn = QPushButton("Восстановить стандартный промпт")
        self.reset_prompt_btn.clicked.connect(self.reset_prompt)
        prompt_layout.addWidget(self.reset_prompt_btn)
        
        layout.addWidget(prompt_group)
        
        # Кнопки
        button_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setStyleSheet(SETTINGS_WINDOW_STYLE)
    
    def reset_prompt(self):
        """Восстанавливает стандартный промпт"""
        self.prompt_input.setText(DEFAULT_LOG_ANALYSIS_PROMPT)
    
    def save_settings(self):
        """Сохранение настроек в .env файл и обновление параметров в родительском окне"""
        url = self.url_input.text().strip()
        api_key = self.key_input.text().strip()
        prompt = self.prompt_input.toPlainText().strip()
        
        # Проверяем корректность URL
        if not url:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Предупреждение", "URL LLM сервера не может быть пустым")
            return
            
        # Убираем слеш в конце URL, если он там есть
        if url.endswith("/"):
            url = url[:-1]
            
        # Проверяем, содержит ли URL схему http/https
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        
        # Обновляем значения в родительском окне
        self.parent().api_url = url
        self.parent().api_key = api_key
        
        # Сохраняем в файл .env
        try:
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(f"LLM_URL={url}\n")
                f.write(f"API_KEY={api_key}\n")
                # Сохраняем промпт в одинарных кавычках, экранируя переносы строк
                escaped_prompt = prompt.replace('\n', '\\n')
                f.write(f"LLM_PROMPT='{escaped_prompt}'\n")
            
            logger.debug(f"Настройки сохранены. URL: {url}, API ключ длина: {len(api_key) if api_key else 0}, длина промпта: {len(prompt)}")
            
            # Сообщаем пользователю о необходимости перезапуска для применения промпта
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Информация", 
                              "Настройки сохранены. Изменения в промпте будут применены при следующем запуске анализа.")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек: {str(e)}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")
            return
        
        self.accept()