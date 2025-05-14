"""
Главное окно приложения
"""

import os
from dotenv import load_dotenv
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QTextEdit, QFileDialog, QProgressBar,
                            QMessageBox)
from core.constants import logger
from core.log_processor import LogProcessor
from core.llm_analyzer import LLMAnalyzer
from ui.settings_window import SettingsWindow
from ui.loading_window import LoadingWindow
from ui.styles import MAIN_STYLE, STATUS_BAR_STYLE
from PySide6.QtGui import QFont

class MainWindow(QMainWindow):
    def __init__(self, vectorizer=None):
        """Инициализация главного окна"""
        super().__init__()
        self.setWindowTitle("AI Log Analyzer")
        self.setMinimumSize(800, 600)
        self.vectorizer = vectorizer
        
        load_dotenv()
        self.api_url = os.getenv('LLM_URL', 'http://localhost:8000')
        self.api_key = os.getenv('API_KEY', '')
        
        logger.debug(f"Инициализация MainWindow с URL: {self.api_url}, API ключ длина: {len(self.api_key) if self.api_key else 0}")
        
        self.statusBar = self.statusBar()
        self.statusBar.setStyleSheet(STATUS_BAR_STYLE)
        
        self._setup_ui()
        self.setStyleSheet(MAIN_STYLE)
        
        # Отключаем кнопки, требующие vectorizer, если он не передан
        if not self.vectorizer:
            self.analyze_btn.setEnabled(False)
            self.clear_db_btn.setEnabled(False)
            logger.debug("Векторайзер не инициализирован, кнопки отключены")
        
        logger.debug("Главное окно инициализировано")
    
    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        button_layout = QHBoxLayout()
        
        self.settings_btn = QPushButton("Настройки")
        self.settings_btn.clicked.connect(self.show_settings)
        button_layout.addWidget(self.settings_btn)
        
        self.select_folder_btn = QPushButton("Выбрать папку")
        self.select_folder_btn.clicked.connect(self.select_folder)
        button_layout.addWidget(self.select_folder_btn)
        
        self.analyze_btn = QPushButton("Анализировать")
        self.analyze_btn.clicked.connect(self.analyze_logs)
        self.analyze_btn.setEnabled(False)
        button_layout.addWidget(self.analyze_btn)
        
        self.clear_db_btn = QPushButton("Очистить БД")
        self.clear_db_btn.clicked.connect(self.clear_vector_db)
        button_layout.addWidget(self.clear_db_btn)
        
        layout.addLayout(button_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.output_text = QTextEdit()
        # Настраиваем QTextEdit для отображения HTML
        self.output_text.setReadOnly(True)
        self.output_text.setAcceptRichText(True)
        self.output_text.setPlaceholderText("Здесь будут отображаться результаты анализа логов...")
        # Увеличиваем высоту текстового поля
        self.output_text.setMinimumHeight(300)
        # Устанавливаем шрифт по умолчанию
        font = QFont("Arial", 10)
        self.output_text.setFont(font)
        layout.addWidget(self.output_text)
    
    def select_folder(self):
        """Диалог выбора папки с логами"""
        try:
            folder_name = QFileDialog.getExistingDirectory(
                self,
                "Выберите папку с логами",
                ""
            )
            
            if not folder_name:
                logger.debug("Пользователь отменил выбор папки")
                return
                
            if not os.path.exists(folder_name):
                logger.error(f"Выбранная папка не существует: {folder_name}")
                QMessageBox.critical(self, "Ошибка", "Выбранная папка не существует.")
                return
                
            self.current_folder = folder_name
            self.analyze_btn.setEnabled(True)
            self.output_text.setText(f"Выбрана папка: {folder_name}")
            logger.debug(f"Выбрана папка для анализа: {folder_name}")
            
        except Exception as e:
            logger.error(f"Ошибка при выборе папки: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось выбрать папку: {str(e)}")
    
    def analyze_logs(self):
        """Анализ выбранной папки с логами"""
        if not hasattr(self, 'current_folder'):
            logger.error("Текущая папка не выбрана")
            QMessageBox.warning(self, "Внимание", "Сначала выберите папку с логами")
            return
            
        if self.vectorizer is None:
            logger.error("Векторайзер не инициализирован")
            QMessageBox.critical(self, "Ошибка", "Векторайзер не инициализирован. Перезапустите приложение")
            return
        
        # Отключаем кнопки на время анализа
        self.select_folder_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.clear_db_btn.setEnabled(False)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.statusBar.showMessage("Обработка логов...")
        logger.debug(f"Начало анализа логов из папки: {self.current_folder}")
        
        try:
            self.log_processor = LogProcessor(self.current_folder)
            self.log_processor.progress.connect(self.update_progress)
            self.log_processor.finished.connect(self.process_finished)
            self.log_processor.error.connect(self.process_error)
            self.log_processor.start()
            logger.debug("LogProcessor запущен")
        except Exception as e:
            logger.error(f"Ошибка при создании LogProcessor: {str(e)}", exc_info=True)
            self.process_error(f"Ошибка при запуске обработки: {str(e)}")
    
    def update_progress(self, message):
        self.output_text.append(message)
        self.statusBar.showMessage(message)
    
    def process_finished(self, processed_logs):
        """Обработка завершения обработки логов и запуск LLM анализа"""
        logger.debug("Обработка логов завершена, запуск LLM анализатора")
        
        # Сохраняем обработанные логи в переменной для последующего восстановления
        self.processed_logs = processed_logs
        
        # Ограничиваем отображаемое количество строк логов, чтобы не перегружать UI
        max_lines = 200
        lines = processed_logs.split('\n')
        total_lines = len(lines)
        
        # Информация о количестве строк
        lines_info = f"[Всего строк логов: {total_lines}]"
        
        if total_lines > max_lines:
            displayed_logs = '\n'.join(lines[:max_lines]) + f"\n\n[...скрыто {total_lines - max_lines} строк...]"
        else:
            displayed_logs = processed_logs
        
        # Создаем HTML-содержимое для отображения логов
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Consolas, Monaco, monospace; margin: 10px; }}
                pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                .log-header {{ font-size: 16px; font-weight: bold; margin-bottom: 10px; }}
                .log-info {{ color: #777; font-style: italic; margin-bottom: 10px; }}
                .log-content {{ background-color: #f8f8f8; border: 1px solid #ddd; padding: 10px; max-height: 400px; overflow-y: auto; }}
                .loading-message {{ font-size: 16px; color: #4CAF50; margin-top: 20px; padding: 10px; background-color: #f0f7f0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="log-header">Обработанные логи:</div>
            <div class="log-info">{lines_info}</div>
            <pre class="log-content">{displayed_logs}</pre>
            <div class="loading-message">Начинаем анализ с помощью LLM...</div>
        </body>
        </html>
        """
        
        # Обновляем текстовое поле с обработанными логами
        self.output_text.setHtml(html_content)
        self.statusBar.showMessage("Анализ с помощью LLM...")
        
        try:
            self.llm_analyzer = LLMAnalyzer(
                self.api_url,
                self.api_key,
                processed_logs,  # Используем полные логи для анализа
                self.vectorizer
            )
            # Явно подключаем сигналы к слотам
            self.llm_analyzer.finished.connect(self.analysis_finished)
            self.llm_analyzer.error.connect(self.analysis_error)
            logger.debug(f"LLM анализатор создан, URL: {self.api_url}, API ключ длина: {len(self.api_key) if self.api_key else 0}")
            self.llm_analyzer.start()
            logger.debug("LLM анализатор запущен")
        except Exception as e:
            logger.error(f"Ошибка при создании LLM анализатора: {str(e)}", exc_info=True)
            self.analysis_error(f"Ошибка при создании LLM анализатора: {str(e)}")
    
    def analysis_finished(self, analysis):
        """Обработка завершения анализа LLM"""
        logger.debug(f"Получен результат анализа LLM, длина: {len(analysis) if analysis else 0}")
        logger.debug(f"Начало результата: {analysis[:100] if analysis else 'пусто'}")
        
        self.progress_bar.setVisible(False)
        
        self.select_folder_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.clear_db_btn.setEnabled(True)
        
        # Сохраняем оригинальный текст для добавления в базу данных
        original_analysis = analysis
        
        # Обрабатываем случаи, когда анализ содержит markdown-разметку
        if analysis:
            try:
                # Подключаем библиотеку для преобразования markdown в html
                try:
                    import markdown
                    # Преобразуем markdown в html
                    html_content = markdown.markdown(analysis)
                    analysis = html_content
                    logger.debug("Использована библиотека markdown для конвертации")
                except ImportError:
                    logger.debug("Библиотека markdown не найдена, используем регулярные выражения")
                    # Заменяем заголовки
                    import re
                    for i in range(6, 0, -1):
                        heading = '#' * i
                        pattern = f"(^|\n){heading} (.+?)(\n|$)"
                        replacement = f"\\1<h{i}>\\2</h{i}>\\3"
                        analysis = re.sub(pattern, replacement, analysis)
                    
                    # Заменяем маркированные списки
                    analysis = re.sub(r'(?:^|\n)- (.+?)(?:\n|$)', r'\n<li>\1</li>\n', analysis)
                    analysis = re.sub(r'(?:^|\n)\* (.+?)(?:\n|$)', r'\n<li>\1</li>\n', analysis)
                    
                    # Группируем списки
                    analysis = re.sub(r'(<li>.+?</li>\n)+', r'<ul>\g<0></ul>', analysis)
                    
                    # Заменяем жирный текст (две звездочки)
                    analysis = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', analysis)
                    
                    # Заменяем жирный текст (два подчеркивания)
                    analysis = re.sub(r'__(.+?)__', r'<b>\1</b>', analysis)
                    
                    # Заменяем курсив (одна звездочка)
                    analysis = re.sub(r'\*([^\*]+?)\*', r'<i>\1</i>', analysis)
                    
                    # Заменяем курсив (одно подчеркивание)
                    analysis = re.sub(r'_([^_]+?)_', r'<i>\1</i>', analysis)
                    
                    # Заменяем блоки кода
                    analysis = re.sub(r'```(?:.+?)?([^`]+?)```', r'<pre style="background-color:#f0f0f0; padding:5px; border:1px solid #ccc;">\1</pre>', analysis, flags=re.DOTALL)
                    
                    # Обработка однострочных блоков кода
                    analysis = re.sub(r'`([^`]+?)`', r'<code style="background-color:#f0f0f0; padding:2px; border:1px solid #ccc;">\1</code>', analysis)
                
                logger.debug("Markdown-разметка обработана для отображения")
            except Exception as e:
                logger.error(f"Ошибка при обработке Markdown: {str(e)}", exc_info=True)
                # В случае ошибки используем исходный текст, заменив переносы строк на <br>
                analysis = original_analysis.replace('\n', '<br>')
        
        # Подготовка информации о логах
        logs_info = ""
        if hasattr(self, 'processed_logs'):
            total_lines = len(self.processed_logs.split('\n'))
            logs_info = f"<div class='logs-summary'>Обработано {total_lines} строк логов</div>"
        
        # Создаем HTML для отображения в QTextEdit с разделами для логов и анализа
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 10px; }}
                pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                code {{ background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; }}
                h1, h2, h3, h4, h5, h6 {{ color: #333; }}
                h1 {{ font-size: 18pt; }}
                h2 {{ font-size: 16pt; }}
                h3 {{ font-size: 14pt; margin-top: 30px; border-bottom: 1px solid #4CAF50; padding-bottom: 5px; }}
                h4 {{ font-size: 12pt; }}
                h5 {{ font-size: 11pt; }}
                h6 {{ font-size: 10pt; }}
                ul {{ margin-left: 20px; }}
                .logs-container {{ margin-bottom: 20px; }}
                .logs-summary {{ color: #777; font-size: 12px; margin-bottom: 5px; }}
                .logs-toggle {{ cursor: pointer; color: #4CAF50; font-weight: bold; }}
                .logs-content {{ display: none; background-color: #f8f8f8; border: 1px solid #ddd; padding: 10px; max-height: 200px; overflow-y: auto; font-family: monospace; }}
                .analysis-header {{ background-color: #4CAF50; color: white; padding: 10px; border-radius: 5px 5px 0 0; }}
                .analysis-content {{ border: 1px solid #4CAF50; border-top: none; padding: 15px; border-radius: 0 0 5px 5px; }}
            </style>
            <script>
                function toggleLogs() {{
                    var content = document.getElementById('logs-content');
                    var toggle = document.getElementById('logs-toggle');
                    if (content.style.display === 'none' || content.style.display === '') {{
                        content.style.display = 'block';
                        toggle.textContent = '▼ Скрыть логи';
                    }} else {{
                        content.style.display = 'none';
                        toggle.textContent = '▶ Показать логи';
                    }}
                }}
            </script>
        </head>
        <body>
            <div class="logs-container">
                {logs_info}
                <div class="logs-toggle" id="logs-toggle" onclick="toggleLogs()">▶ Показать логи</div>
                <pre class="logs-content" id="logs-content">{self.processed_logs[:5000] if hasattr(self, 'processed_logs') else ""}</pre>
            </div>
            <div class="analysis-header">Результаты анализа LLM</div>
            <div class="analysis-content">{analysis}</div>
        </body>
        </html>
        """
        
        # Очищаем текстовое поле и устанавливаем HTML-содержимое
        self.output_text.clear()
        self.output_text.setHtml(html_content)
        
        try:
            # Сохраняем результат в векторной базе (оригинальный текст без HTML-разметки)
            self.vectorizer.add_to_db(original_analysis)
        except Exception as e:
            logger.error(f"Ошибка при сохранении результата в базе: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "Предупреждение", f"Не удалось сохранить результат в базе: {str(e)}")
        
        self.statusBar.showMessage("Анализ завершен")
    
    def process_error(self, error_message):
        self.progress_bar.setVisible(False)
        
        self.select_folder_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.clear_db_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Ошибка", error_message)
        
        self.statusBar.showMessage("Ошибка при обработке")
    
    def analysis_error(self, error_message):
        self.progress_bar.setVisible(False)
        
        self.select_folder_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.clear_db_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Ошибка", error_message)
        
        self.statusBar.showMessage("Ошибка при анализе")
    
    def clear_vector_db(self):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите очистить базу данных?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.statusBar.showMessage("Очистка базы данных...")
                self.vectorizer.clear_db()
                self.output_text.append("\nВекторная база данных очищена")
                self.statusBar.showMessage("База данных очищена")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось очистить базу данных: {str(e)}")
                self.statusBar.showMessage("Ошибка при очистке базы данных")
    
    def show_vector_db_info(self):
        try:
            stats = self.vectorizer.get_stats()
            if stats:
                message = f"""
                Статистика базы данных:
                Всего записей: {stats['total_records']}
                Размерность векторов: {stats['dimension']}
                Директория: {stats['directory']}
                """
                self.output_text.append(message)
            else:
                self.output_text.append("\nНе удалось получить статистику базы данных")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить статистику: {str(e)}")
    
    def show_settings(self):
        settings_window = SettingsWindow(self)
        settings_window.exec()
    
    def show_loading(self):
        self.loading_window = LoadingWindow(self)
        self.loading_window.show()
    
    def hide_loading(self):
        if hasattr(self, 'loading_window'):
            self.loading_window.close()
    
    def set_vectorizer(self, vectorizer):
        """Устанавливает векторизатор и обновляет UI"""
        if vectorizer is None:
            logger.error("Попытка установить пустой векторизатор")
            return False
            
        try:
            self.vectorizer = vectorizer
            logger.debug("Векторизатор установлен в MainWindow")
            
            # Включаем кнопки, зависящие от векторизатора
            self.clear_db_btn.setEnabled(True)
            
            # Кнопка анализа включается только если выбрана папка
            if hasattr(self, 'current_folder') and os.path.exists(self.current_folder):
                self.analyze_btn.setEnabled(True)
                logger.debug("Кнопка анализа активирована")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке векторизатора: {str(e)}", exc_info=True)
            return False 