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
        super().__init__()
        self.setWindowTitle("AI Log Analyzer")
        self.setMinimumSize(800, 600)
        self.vectorizer = vectorizer
        load_dotenv()
        self.api_url = os.getenv('LLM_URL', 'http://localhost:8000')
        self.api_key = os.getenv('API_KEY', '')
        logger.debug(f"Initializing MainWindow with URL: {self.api_url}, API key length: {len(self.api_key) if self.api_key else 0}")
        self.statusBar = self.statusBar()
        self.statusBar.setStyleSheet(STATUS_BAR_STYLE)
        self._setup_ui()
        self.setStyleSheet(MAIN_STYLE)
        if not self.vectorizer:
            self.analyze_btn.setEnabled(False)
            self.clear_db_btn.setEnabled(False)
            logger.debug("Vectorizer not initialized, buttons disabled")
        logger.debug("Main window initialized")

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        button_layout = QHBoxLayout()
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        button_layout.addWidget(self.settings_btn)
        self.select_folder_btn = QPushButton("Select folder")
        self.select_folder_btn.clicked.connect(self.select_folder)
        button_layout.addWidget(self.select_folder_btn)
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.clicked.connect(self.analyze_logs)
        self.analyze_btn.setEnabled(False)
        button_layout.addWidget(self.analyze_btn)
        self.clear_db_btn = QPushButton("Clear DB")
        self.clear_db_btn.clicked.connect(self.clear_vector_db)
        button_layout.addWidget(self.clear_db_btn)
        layout.addLayout(button_layout)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setAcceptRichText(True)
        self.output_text.setPlaceholderText("Analysis results will be displayed here...")
        self.output_text.setMinimumHeight(300)
        font = QFont("Arial", 10)
        self.output_text.setFont(font)
        layout.addWidget(self.output_text)
    
    def select_folder(self):
        try:
            folder_name = QFileDialog.getExistingDirectory(
                self,
                "Select log folder",
                ""
            )
            if not folder_name:
                logger.debug("User cancelled folder selection")
                return
            if not os.path.exists(folder_name):
                logger.error(f"Selected folder does not exist: {folder_name}")
                QMessageBox.critical(self, "Error", "Selected folder does not exist.")
                return
            self.current_folder = folder_name
            self.analyze_btn.setEnabled(True)
            self.output_text.setText(f"Selected folder: {folder_name}")
            logger.debug(f"Folder selected for analysis: {folder_name}")
        except Exception as e:
            logger.error(f"Error selecting folder: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to select folder: {str(e)}")
    
    def analyze_logs(self):
        if not hasattr(self, 'current_folder'):
            logger.error("Current folder not selected")
            QMessageBox.warning(self, "Warning", "Please select a folder with logs first")
            return
            
        if self.vectorizer is None:
            logger.error("Vectorizer not initialized")
            QMessageBox.critical(self, "Error", "Vectorizer not initialized. Restart the application")
            return
        
        self.select_folder_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.clear_db_btn.setEnabled(False)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.statusBar.showMessage("Processing logs...")
        logger.debug(f"Starting log analysis from folder: {self.current_folder}")
        
        try:
            self.log_processor = LogProcessor(self.current_folder)
            self.log_processor.progress.connect(self.update_progress)
            self.log_processor.finished.connect(self.process_finished)
            self.log_processor.error.connect(self.process_error)
            self.log_processor.start()
            logger.debug("LogProcessor started")
        except Exception as e:
            logger.error(f"Error creating LogProcessor: {str(e)}", exc_info=True)
            self.process_error(f"Error starting processing: {str(e)}")
    
    def update_progress(self, message):
        self.output_text.append(message)
        self.statusBar.showMessage(message)
    
    def process_finished(self, processed_logs):
        logger.debug("Log processing finished, starting LLM analysis")
        self.processed_logs = processed_logs
        max_lines = 200
        lines = processed_logs.split('\n')
        total_lines = len(lines)
        lines_info = f"[Total log lines: {total_lines}]"
        if total_lines > max_lines:
            displayed_logs = '\n'.join(lines[:max_lines]) + f"\n\n[...hidden {total_lines - max_lines} lines...]"
        else:
            displayed_logs = processed_logs
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
            <div class="log-header">Processed logs:</div>
            <div class="log-info">{lines_info}</div>
            <pre class="log-content">{displayed_logs}</pre>
            <div class="loading-message">Starting analysis with LLM...</div>
        </body>
        </html>
        """
        self.output_text.setHtml(html_content)
        self.statusBar.showMessage("Analyzing with LLM...")
        try:
            self.llm_analyzer = LLMAnalyzer(
                self.api_url,
                self.api_key,
                processed_logs,
                self.vectorizer
            )
            self.llm_analyzer.finished.connect(self.analysis_finished)
            self.llm_analyzer.error.connect(self.analysis_error)
            logger.debug(f"LLM analyzer created, URL: {self.api_url}, API key length: {len(self.api_key) if self.api_key else 0}")
            self.llm_analyzer.start()
            logger.debug("LLM analyzer started")
        except Exception as e:
            logger.error(f"Error creating LLM analyzer: {str(e)}", exc_info=True)
            self.analysis_error(f"Error creating LLM analyzer: {str(e)}")
    
    def analysis_finished(self, analysis):
        logger.debug(f"LLM analysis result received, length: {len(analysis) if analysis else 0}")
        logger.debug(f"Result start: {analysis[:100] if analysis else 'empty'}")
        self.progress_bar.setVisible(False)
        self.select_folder_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.clear_db_btn.setEnabled(True)
        original_analysis = analysis
        if analysis:
            try:
                try:
                    import markdown
                    html_content = markdown.markdown(analysis)
                    analysis = html_content
                    logger.debug("Markdown library used for conversion")
                except ImportError:
                    logger.debug("Markdown library not found, using regex")
                    import re
                    for i in range(6, 0, -1):
                        heading = '#' * i
                        pattern = f"(^|\n){heading} (.+?)(\n|$)"
                        replacement = f"\\1<h{i}>\\2</h{i}>\\3"
                        analysis = re.sub(pattern, replacement, analysis)
                    analysis = re.sub(r'(?:^|\n)- (.+?)(?:\n|$)', r'\n<li>\1</li>\n', analysis)
                    analysis = re.sub(r'(?:^|\n)\* (.+?)(?:\n|$)', r'\n<li>\1</li>\n', analysis)
                    analysis = re.sub(r'(<li>.+?</li>\n)+', r'<ul>\g<0></ul>', analysis)
                    analysis = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', analysis)
                    analysis = re.sub(r'__(.+?)__', r'<b>\1</b>', analysis)
                    analysis = re.sub(r'\*([^\*]+?)\*', r'<i>\1</i>', analysis)
                    analysis = re.sub(r'_([^_]+?)_', r'<i>\1</i>', analysis)
                    analysis = re.sub(r'```(?:.+?)?([^`]+?)```', r'<pre style="background-color:#f0f0f0; padding:5px; border:1px solid #ccc;">\1</pre>', analysis, flags=re.DOTALL)
                    analysis = re.sub(r'`([^`]+?)`', r'<code style="background-color:#f0f0f0; padding:2px; border:1px solid #ccc;">\1</code>', analysis)
                logger.debug("Markdown formatting processed for display")
            except Exception as e:
                logger.error(f"Error processing Markdown: {str(e)}", exc_info=True)
                analysis = original_analysis.replace('\n', '<br>')
        logs_info = ""
        if hasattr(self, 'processed_logs'):
            total_lines = len(self.processed_logs.split('\n'))
            logs_info = f"<div class='logs-summary'>Processed {total_lines} log lines</div>"
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
                        toggle.textContent = '▼ Hide logs';
                    }} else {{
                        content.style.display = 'none';
                        toggle.textContent = '▶ Show logs';
                    }}
                }}
            </script>
        </head>
        <body>
            <div class="logs-container">
                {logs_info}
                <div class="logs-toggle" id="logs-toggle" onclick="toggleLogs()">▶ Show logs</div>
                <pre class="logs-content" id="logs-content">{self.processed_logs[:5000] if hasattr(self, 'processed_logs') else ""}</pre>
            </div>
            <div class="analysis-header">LLM Analysis Results</div>
            <div class="analysis-content">{analysis}</div>
        </body>
        </html>
        """
        self.output_text.clear()
        self.output_text.setHtml(html_content)
        try:
            self.vectorizer.add_to_db(original_analysis)
        except Exception as e:
            logger.error(f"Error saving result to database: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "Warning", f"Failed to save result to database: {str(e)}")
        self.statusBar.showMessage("Analysis complete")
    
    def process_error(self, error_message):
        self.progress_bar.setVisible(False)
        self.select_folder_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.clear_db_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", error_message)
        self.statusBar.showMessage("Processing error")
    
    def analysis_error(self, error_message):
        self.progress_bar.setVisible(False)
        self.select_folder_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.clear_db_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", error_message)
        self.statusBar.showMessage("Analysis error")
    
    def clear_vector_db(self):
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Are you sure you want to clear the database?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.statusBar.showMessage("Clearing database...")
                self.vectorizer.clear_db()
                self.output_text.append("\nVector database cleared")
                self.statusBar.showMessage("Database cleared")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear database: {str(e)}")
                self.statusBar.showMessage("Database clearing error")
    
    def show_vector_db_info(self):
        try:
            stats = self.vectorizer.get_stats()
            if stats:
                message = f"""
                Database statistics:
                Total records: {stats['total_records']}
                Vector dimension: {stats['dimension']}
                Directory: {stats['directory']}
                """
                self.output_text.append(message)
            else:
                self.output_text.append("\nFailed to retrieve database statistics")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to retrieve statistics: {str(e)}")
    
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
        if vectorizer is None:
            logger.error("Attempt to set empty vectorizer")
            return False
        try:
            self.vectorizer = vectorizer
            logger.debug("Vectorizer set in MainWindow")
            self.clear_db_btn.setEnabled(True)
            if hasattr(self, 'current_folder') and os.path.exists(self.current_folder):
                self.analyze_btn.setEnabled(True)
                logger.debug("Analyze button activated")
            return True
        except Exception as e:
            logger.error(f"Error setting vectorizer: {str(e)}", exc_info=True)
            return False