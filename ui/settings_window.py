from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QTextEdit, QGroupBox, QComboBox)
from PySide6.QtCore import Qt
from ui.styles import SETTINGS_WINDOW_STYLE
import os
from core.prompts import DEFAULT_LOG_ANALYSIS_PROMPT
from core.constants import logger

LABELS = {
    'en': {
        'window_title': "Settings",
        'api_group': "API Settings",
        'url_label': "LLM server URL:",
        'key_label': "API Key:",
        'prompt_group': "Prompt Settings",
        'prompt_label': "Analysis prompt:",
        'reset_prompt': "Reset to default prompt",
        'save': "Save",
        'cancel': "Cancel",
        'info_saved': "Settings saved. Changes to the prompt will be applied on the next analysis run.",
        'error_save': "Failed to save settings:",
        'warning_url': "LLM server URL cannot be empty",
        'language_label': "Language:",
        'temperature_label': "Temperature:",
        'max_tokens_label': "Max tokens:",
        'select_language': "Select language",
        'en': "English",
        'ru': "Russian"
    },
    'ru': {
        'window_title': "Настройки",
        'api_group': "Настройки API",
        'url_label': "URL LLM сервера:",
        'key_label': "API ключ:",
        'prompt_group': "Настройки промпта",
        'prompt_label': "Промпт для анализа:",
        'reset_prompt': "Сбросить промпт по умолчанию",
        'save': "Сохранить",
        'cancel': "Отмена",
        'info_saved': "Настройки сохранены. Изменения в промпте будут применены при следующем запуске анализа.",
        'error_save': "Не удалось сохранить настройки:",
        'warning_url': "URL LLM сервера не может быть пустым",
        'language_label': "Язык:",
        'temperature_label': "Температура:",
        'max_tokens_label': "Максимум токенов:",
        'select_language': "Выберите язык",
        'en': "Английский",
        'ru': "Русский"
    }
}

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.language = os.getenv('APP_LANG', 'ru')
        self.labels = LABELS[self.language]
        self.setWindowTitle(self.labels['window_title'])
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_label = QLabel(self.labels['language_label'])
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(self.labels['ru'], 'ru')
        self.lang_combo.addItem(self.labels['en'], 'en')
        self.lang_combo.setCurrentIndex(0 if self.language == 'ru' else 1)
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        # Set style for better contrast
        lang_label.setStyleSheet('color: #222; background: transparent; font-weight: bold;')
        self.lang_combo.setStyleSheet('background: #f5f5f5; color: #222; border: 1px solid #bbb; border-radius: 4px; min-width: 120px;')
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)
        
        # API settings group
        api_group = QGroupBox(self.labels['api_group'])
        api_layout = QVBoxLayout(api_group)
        
        url_layout = QHBoxLayout()
        url_label = QLabel(self.labels['url_label'])
        self.url_input = QLineEdit()
        self.url_input.setText(parent.api_url)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        api_layout.addLayout(url_layout)
        
        key_layout = QHBoxLayout()
        key_label = QLabel(self.labels['key_label'])
        self.key_input = QLineEdit()
        self.key_input.setText(parent.api_key)
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        api_layout.addLayout(key_layout)
        
        layout.addWidget(api_group)
        
        # Prompt settings group
        prompt_group = QGroupBox(self.labels['prompt_group'])
        prompt_layout = QVBoxLayout(prompt_group)
        
        prompt_label = QLabel(self.labels['prompt_label'])
        prompt_layout.addWidget(prompt_label)
        
        self.prompt_input = QTextEdit()
        self.prompt_input.setMinimumHeight(200)
        
        # Load current prompt from .env or use default
        current_prompt = os.getenv('LLM_PROMPT', DEFAULT_LOG_ANALYSIS_PROMPT)
        self.prompt_input.setText(current_prompt)
        
        prompt_layout.addWidget(self.prompt_input)
        
        # Button to reset to default prompt
        self.reset_prompt_btn = QPushButton(self.labels['reset_prompt'])
        self.reset_prompt_btn.clicked.connect(self.reset_prompt)
        prompt_layout.addWidget(self.reset_prompt_btn)
        
        layout.addWidget(prompt_group)
        
        # LLM params
        llm_params_layout = QHBoxLayout()
        temp_label = QLabel(self.labels['temperature_label'])
        self.temp_input = QLineEdit(os.getenv('LLM_TEMPERATURE', '1.0'))
        max_tokens_label = QLabel(self.labels['max_tokens_label'])
        self.max_tokens_input = QLineEdit(os.getenv('LLM_MAX_TOKENS', '1024'))
        llm_params_layout.addWidget(temp_label)
        llm_params_layout.addWidget(self.temp_input)
        llm_params_layout.addWidget(max_tokens_label)
        llm_params_layout.addWidget(self.max_tokens_input)
        layout.addLayout(llm_params_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton(self.labels['save'])
        save_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton(self.labels['cancel'])
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setStyleSheet(SETTINGS_WINDOW_STYLE)

    def change_language(self):
        lang = self.lang_combo.currentData()
        self.language = lang
        self.labels = LABELS[lang]
        os.environ['APP_LANG'] = lang
        self.setWindowTitle(self.labels['window_title'])
        self.lang_combo.setItemText(0, self.labels['ru'])
        self.lang_combo.setItemText(1, self.labels['en'])
        self.reset_prompt_btn.setText(self.labels['reset_prompt'])
        # Update all labels (for brevity, only main ones)
        self.findChild(QGroupBox).setTitle(self.labels['api_group'])
        self.findChildren(QLabel)[0].setText(self.labels['url_label'])
        self.findChildren(QLabel)[1].setText(self.labels['key_label'])
        self.findChildren(QGroupBox)[1].setTitle(self.labels['prompt_group'])
        self.findChildren(QLabel)[2].setText(self.labels['prompt_label'])
        self.findChildren(QPushButton)[0].setText(self.labels['reset_prompt'])
        self.findChildren(QPushButton)[1].setText(self.labels['save'])
        self.findChildren(QPushButton)[2].setText(self.labels['cancel'])
        self.findChildren(QLabel)[3].setText(self.labels['temperature_label'])
        self.findChildren(QLabel)[4].setText(self.labels['max_tokens_label'])

    def reset_prompt(self):
        """Resets to the default prompt"""
        self.prompt_input.setText(DEFAULT_LOG_ANALYSIS_PROMPT)
    
    def save_settings(self):
        """Save settings to .env file and update parameters in the parent window"""
        url = self.url_input.text().strip()
        api_key = self.key_input.text().strip()
        prompt = self.prompt_input.toPlainText().strip()
        temperature = self.temp_input.text().strip()
        max_tokens = self.max_tokens_input.text().strip()
        lang = self.lang_combo.currentData()
        
        # Validate URL
        if not url:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Warning", self.labels['warning_url'])
            return
            
        # Remove trailing slash from URL if present
        if url.endswith("/"):
            url = url[:-1]
            
        # Ensure URL has http/https scheme
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        
        # Update values in the parent window
        self.parent().api_url = url
        self.parent().api_key = api_key
        
        # Save to .env file
        try:
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(f"LLM_URL={url}\n")
                f.write(f"API_KEY={api_key}\n")
                # Save prompt in single quotes, escaping newlines
                escaped_prompt = prompt.replace('\n', '\\n')
                f.write(f"LLM_PROMPT='{escaped_prompt}'\n")
                f.write(f"LLM_TEMPERATURE={temperature}\n")
                f.write(f"LLM_MAX_TOKENS={max_tokens}\n")
                f.write(f"APP_LANG={lang}\n")
            
            logger.debug(f"Settings saved. URL: {url}, API key length: {len(api_key) if api_key else 0}, prompt length: {len(prompt)}, temp: {temperature}, max_tokens: {max_tokens}, lang: {lang}")
            
            # Notify user about the need to restart for prompt changes to take effect
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Info", 
                              self.labels['info_saved'])
            
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"{self.labels['error_save']} {str(e)}")
            return
        
        self.accept()