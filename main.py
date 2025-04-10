import sys
import os
import json
import numpy as np
import zipfile
import tarfile
import rarfile
import tempfile
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QTextEdit, QLabel,
                            QFileDialog, QMessageBox, QProgressBar, QDialog,
                            QLineEdit)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from dotenv import load_dotenv
import requests
import faiss
from transformers import AutoTokenizer, AutoModel
import torch
import logging
from multiprocessing import Pool, cpu_count
import win32evtlog
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LoadingWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Загрузка")
        self.setFixedSize(300, 100)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        
        layout = QVBoxLayout(self)
        
        self.loading_label = QLabel("Инициализация приложения...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.loading_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Бесконечный прогресс
        layout.addWidget(self.progress_bar)
        
        self.setStyleSheet("""
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
        """)

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setFixedSize(400, 150)
        
        layout = QVBoxLayout(self)
        
        url_layout = QHBoxLayout()
        url_label = QLabel("URL LLM сервера:")
        self.url_input = QLineEdit()
        self.url_input.setText(parent.api_url)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        key_layout = QHBoxLayout()
        key_label = QLabel("API Key:")
        self.key_input = QLineEdit()
        self.key_input.setText(parent.api_key)
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        layout.addLayout(key_layout)
        
        button_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setStyleSheet("""
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
        """)
    
    def save_settings(self):
        self.parent().api_url = self.url_input.text()
        self.parent().api_key = self.key_input.text()
        
        with open('.env', 'w') as f:
            f.write(f"LLM_URL={self.url_input.text()}\n")
            f.write(f"API_KEY={self.key_input.text()}\n")
        
        self.accept()

def process_file_wrapper(args):
    file_path, supported_extensions, supported_archives, temp_dir = args
    return LogProcessor.process_file_parallel(
        file_path,
        supported_extensions,
        supported_archives,
        temp_dir
    )

class LogProcessor(QThread):
    progress = Signal(str)
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.supported_extensions = {
            '.log', '.txt', '.evtx', '.json', '.jsonl', '.csv',
            '.xml', '.yaml', '.yml', '.ini', '.conf', '.out',
            '.err', '.debug', '.trace', '.audit', '.syslog'
        }
        self.supported_archives = {'.zip', '.gz', '.tar', '.rar'}
        self.temp_dir = None
        self.num_processes = min(2, max(1, cpu_count() - 1))
        logger.debug(f"Инициализация LogProcessor с папкой: {folder_path}")
    
    def __del__(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.error(f"Ошибка при удалении временной директории: {e}")
    
    @staticmethod
    def process_evtx_file(file_path):
        try:
            processed_lines = []
            server = 'localhost'
            logtype = 'System'
            hand = win32evtlog.OpenEventLog(server, logtype)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            
            max_events = 1000
            
            while True:
                events = win32evtlog.ReadEventLog(hand, flags, 0)
                if not events:
                    break
                    
                for event in events:
                    try:
                        if len(processed_lines) >= max_events:
                            break
                            
                        event_data = {
                            'EventID': event.EventID,
                            'TimeGenerated': event.TimeGenerated.strftime('%Y-%m-%d %H:%M:%S'),
                            'SourceName': event.SourceName,
                            'EventType': event.EventType,
                            'EventCategory': event.EventCategory,
                            'StringInserts': event.StringInserts,
                            'ComputerName': event.ComputerName,
                            'Sid': event.Sid
                        }
                        
                        if event.StringInserts:
                            message = ' | '.join(str(x) for x in event.StringInserts if x)
                        else:
                            message = event.SourceName
                            
                        formatted_line = (
                            f"EventID: {event_data['EventID']} | "
                            f"Time: {event_data['TimeGenerated']} | "
                            f"Source: {event_data['SourceName']} | "
                            f"Type: {event_data['EventType']} | "
                            f"Category: {event_data['EventCategory']} | "
                            f"Message: {message}"
                        )
                        processed_lines.append(formatted_line)
                    except Exception as e:
                        logger.error(f"Ошибка при обработке события: {str(e)}")
                        continue
                
                if len(processed_lines) >= max_events:
                    break
            
            win32evtlog.CloseEventLog(hand)
            return processed_lines
            
        except Exception as e:
            logger.error(f"Ошибка при обработке журнала событий {file_path}: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def parse_json_log(file_path):
        try:
            processed_lines = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        formatted_entry = json.dumps(log_entry, ensure_ascii=False, indent=2)
                        processed_lines.append(formatted_entry)
                    except json.JSONDecodeError:
                        if line.strip():
                            processed_lines.append(line.strip())
            return processed_lines
        except Exception as e:
            logger.error(f"Ошибка при обработке JSON файла {file_path}: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def parse_csv_log(file_path):
        try:
            processed_lines = []
            with open(file_path, 'r', encoding='utf-8') as f:
                header = f.readline().strip().split(',')
                for line in f:
                    if line.strip():
                        values = line.strip().split(',')
                        formatted_line = " | ".join(f"{h}: {v}" for h, v in zip(header, values))
                        processed_lines.append(formatted_line)
            return processed_lines
        except Exception as e:
            logger.error(f"Ошибка при обработке CSV файла {file_path}: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def parse_xml_log(file_path):
        try:
            import xml.etree.ElementTree as ET
            processed_lines = []
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            def process_element(element, level=0):
                indent = "  " * level
                tag = element.tag
                text = element.text.strip() if element.text else ""
                processed_lines.append(f"{indent}{tag}: {text}")
                for child in element:
                    process_element(child, level + 1)
            
            process_element(root)
            return processed_lines
        except Exception as e:
            logger.error(f"Ошибка при обработке XML файла {file_path}: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def parse_yaml_log(file_path):
        try:
            import yaml
            processed_lines = []
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data:
                    formatted_data = yaml.dump(data, allow_unicode=True, default_flow_style=False)
                    processed_lines.append(formatted_data)
            return processed_lines
        except Exception as e:
            logger.error(f"Ошибка при обработке YAML файла {file_path}: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def parse_ini_log(file_path):
        try:
            import configparser
            processed_lines = []
            config = configparser.ConfigParser()
            config.read(file_path, encoding='utf-8')
            
            for section in config.sections():
                processed_lines.append(f"[{section}]")
                for key, value in config.items(section):
                    processed_lines.append(f"{key} = {value}")
            return processed_lines
        except Exception as e:
            logger.error(f"Ошибка при обработке INI файла {file_path}: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def parse_syslog(file_path):
        try:
            processed_lines = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        match = re.match(r'<(\d+)>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z) (\S+) (\S+): (.*)', line.strip())
                        if match:
                            priority, timestamp, host, program, message = match.groups()
                            formatted_line = f"Priority: {priority} | Time: {timestamp} | Host: {host} | Program: {program} | Message: {message}"
                        else:
                            formatted_line = line.strip()
                        processed_lines.append(formatted_line)
            return processed_lines
        except Exception as e:
            logger.error(f"Ошибка при обработке Syslog файла {file_path}: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def extract_archive(archive_path, temp_dir):
        try:
            if not temp_dir:
                temp_dir = tempfile.mkdtemp()
            
            ext = os.path.splitext(archive_path)[1].lower()
            
            if ext == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                    return True
            elif ext in {'.tar', '.gz'}:
                with tarfile.open(archive_path, 'r:*') as tar_ref:
                    tar_ref.extractall(temp_dir)
                    return True
            elif ext == '.rar':
                with rarfile.RarFile(archive_path, 'r') as rar_ref:
                    rar_ref.extractall(temp_dir)
                    return True
            else:
                logger.warning(f"Неподдерживаемый формат архива: {ext}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при распаковке архива {archive_path}: {e}")
            return False
    
    def get_files_to_process(self, directory):
        files_to_process = []
        try:
            if not os.path.exists(directory):
                error_msg = f"Директория не существует: {directory}"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return []
            
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self.supported_extensions or ext in self.supported_archives:
                        files_to_process.append(file_path)
            
            if not files_to_process:
                error_msg = f"В директории {directory} не найдено поддерживаемых файлов"
                logger.warning(error_msg)
                self.error.emit(error_msg)
                return []
            
            logger.debug(f"Найдено файлов для обработки: {len(files_to_process)}")
            return files_to_process
            
        except Exception as e:
            error_msg = f"Ошибка при получении списка файлов: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            return []
    
    @staticmethod
    def process_file_parallel(file_path, supported_extensions, supported_archives, temp_dir=None):
        try:
            if not os.path.exists(file_path):
                logger.error(f"Файл не существует: {file_path}")
                return []
            
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.evtx':
                logger.debug(f"Обработка файла .evtx: {file_path}")
                return LogProcessor.process_evtx_file(file_path)
            
            if ext in {'.json', '.jsonl'}:
                logger.debug(f"Обработка JSON файла: {file_path}")
                return LogProcessor.parse_json_log(file_path)
            
            if ext == '.csv':
                logger.debug(f"Обработка CSV файла: {file_path}")
                return LogProcessor.parse_csv_log(file_path)
            
            if ext == '.xml':
                logger.debug(f"Обработка XML файла: {file_path}")
                return LogProcessor.parse_xml_log(file_path)
            
            if ext in {'.yaml', '.yml'}:
                logger.debug(f"Обработка YAML файла: {file_path}")
                return LogProcessor.parse_yaml_log(file_path)
            
            if ext in {'.ini', '.conf'}:
                logger.debug(f"Обработка INI файла: {file_path}")
                return LogProcessor.parse_ini_log(file_path)
            
            if ext == '.syslog':
                logger.debug(f"Обработка Syslog файла: {file_path}")
                return LogProcessor.parse_syslog(file_path)
            
            if ext in supported_archives:
                logger.debug(f"Обработка архива: {file_path}")
                
                if LogProcessor.extract_archive(file_path, temp_dir):
                    processed_lines = []
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            file_ext = os.path.splitext(file)[1].lower()
                            
                            if file_ext in supported_extensions:
                                try:
                                    if file_ext == '.evtx':
                                        processed_lines.extend(LogProcessor.process_evtx_file(file_path))
                                    elif file_ext in {'.json', '.jsonl'}:
                                        processed_lines.extend(LogProcessor.parse_json_log(file_path))
                                    elif file_ext == '.csv':
                                        processed_lines.extend(LogProcessor.parse_csv_log(file_path))
                                    elif file_ext == '.xml':
                                        processed_lines.extend(LogProcessor.parse_xml_log(file_path))
                                    elif file_ext in {'.yaml', '.yml'}:
                                        processed_lines.extend(LogProcessor.parse_yaml_log(file_path))
                                    elif file_ext in {'.ini', '.conf'}:
                                        processed_lines.extend(LogProcessor.parse_ini_log(file_path))
                                    elif file_ext == '.syslog':
                                        processed_lines.extend(LogProcessor.parse_syslog(file_path))
                                    else:
                                        with open(file_path, 'r', encoding='utf-8') as f:
                                            lines = f.readlines()
                                            for line in lines:
                                                line = line.strip()
                                                if line:
                                                    processed_lines.append(line)
                                except Exception as e:
                                    logger.error(f"Ошибка при чтении файла {file}: {str(e)}")
                    
                    return processed_lines
                else:
                    logger.warning(f"Не удалось распаковать архив: {file_path}")
                    return []
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                encodings = ['cp1251', 'latin1', 'ascii']
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            lines = f.readlines()
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    logger.error(f"Не удалось прочитать файл {file_path}: неподдерживаемая кодировка")
                    return []
            
            processed_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    processed_lines.append(line)
            
            return processed_lines
            
        except Exception as e:
            logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}", exc_info=True)
            return []
    
    def run(self):
        try:
            logger.debug("Начало обработки директории")
            
            files_to_process = self.get_files_to_process(self.folder_path)
            
            if not files_to_process:
                return
            
            logger.debug(f"Найдено файлов для обработки: {len(files_to_process)}")
            
            all_lines = []
            max_lines = 10000
            current_lines = 0
            
            for file_path in files_to_process:
                try:
                    if current_lines >= max_lines:
                        logger.warning(f"Достигнут лимит строк ({max_lines}). Обработка остановлена.")
                        break
                        
                    result = LogProcessor.process_file_parallel(
                        file_path,
                        self.supported_extensions,
                        self.supported_archives,
                        self.temp_dir
                    )
                    
                    remaining_lines = max_lines - current_lines
                    if remaining_lines > 0:
                        lines_to_add = result[:remaining_lines]
                        all_lines.extend(lines_to_add)
                        current_lines += len(lines_to_add)
                        
                except Exception as e:
                    error_msg = f"Ошибка при обработке файла {file_path}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    self.error.emit(error_msg)
                    continue
            
            if not all_lines:
                error_msg = "Не удалось обработать ни один файл"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return
            
            logger.debug(f"Обработано {len(all_lines)} строк")
            
            processed_text = "\n".join(all_lines)
            logger.debug("Обработка завершена")
            self.finished.emit(processed_text)
            
        except Exception as e:
            error_msg = f"Ошибка при обработке: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)

class LLMAnalyzer(QThread):
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, api_url, api_key, log_text, vectorizer):
        super().__init__()
        self.api_url = api_url
        self.api_key = api_key
        self.log_text = log_text
        self.vectorizer = vectorizer
        logger.debug("Инициализация LLMAnalyzer")
        
    def run(self):
        try:
            logger.debug("Начало анализа с помощью LLM")
            embeddings = self.vectorizer.get_embeddings(self.log_text)
            logger.debug("Получены эмбеддинги")
            
            similar_logs = self.vectorizer.search(embeddings, k=2)
            logger.debug("Найдены похожие логи")
            
            max_chars = 1500
            truncated_logs = self.log_text[:max_chars] + "..." if len(self.log_text) > max_chars else self.log_text
            truncated_similar = similar_logs[:max_chars] + "..." if len(similar_logs) > max_chars else similar_logs
            
            prompt = f"""Проанализируй следующие логи. Предоставь:
            1. Краткое описание проблемы
            2. Возможные причины
            3. Рекомендации по исправлению
            
            Текущие логи:
            {truncated_logs}
            
            Похожие логи:
            {truncated_similar}
            """
            
            logger.debug("Отправка запроса к LLM")
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            data = {
                "model": "default",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            endpoint = "/v1/chat/completions"
            api_url = f"{self.api_url}{endpoint}"
            logger.debug(f"Отправка запроса на URL: {api_url}")
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Получен ответ: {result}")
            
            if isinstance(result, dict) and "choices" in result and len(result["choices"]) > 0:
                analysis = result["choices"][0]["message"]["content"]
            else:
                analysis = str(result)
                
            logger.debug("Получен ответ от LLM")
            
            self.finished.emit(analysis)
            
        except Exception as e:
            logger.error(f"Ошибка при анализе: {str(e)}", exc_info=True)
            self.error.emit(f"Ошибка при анализе: {str(e)}")

class Vectorizer:
    def __init__(self):
        logger.debug("Инициализация Vectorizer")
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/MiniLM-L12-H384-uncased")
        self.model = AutoModel.from_pretrained("microsoft/MiniLM-L12-H384-uncased")
        self.dimension = 384
        self.index = None
        self.metadata = []
        self.db_path = "./vector_db"
        self._init_db()
        logger.debug("Vectorizer инициализирован")
    
    def _init_db(self):
        try:
            logger.debug("Инициализация базы данных")
            os.makedirs(self.db_path, exist_ok=True)
            
            self.index = faiss.IndexFlatL2(self.dimension)
            
            metadata_path = os.path.join(self.db_path, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            
            logger.debug(f"База данных инициализирована. Количество записей: {len(self.metadata)}")
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}", exc_info=True)
            raise
    
    def get_embeddings(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
        
        return embeddings[0].numpy().astype(np.float64)
    
    def add_to_db(self, text):
        try:
            embeddings = self.get_embeddings(text)
            
            self.index.add(np.array([embeddings], dtype=np.float64))
            
            self.metadata.append(text)
            
            metadata_path = os.path.join(self.db_path, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            index_path = os.path.join(self.db_path, "faiss.index")
            faiss.write_index(self.index, index_path)
            
            return True
        except Exception as e:
            print(f"Ошибка при добавлении в базу данных: {e}")
            return False
    
    def search(self, query_embeddings, k=5):
        try:
            distances, indices = self.index.search(np.array([query_embeddings], dtype=np.float64), k)
            
            results = []
            for idx in indices[0]:
                if idx < len(self.metadata):
                    results.append(self.metadata[idx])
            
            return "\n".join(results)
        except Exception as e:
            print(f"Ошибка при поиске: {e}")
            return ""
    
    def clear_db(self):
        try:
            self.index = faiss.IndexFlatL2(self.dimension)
            
            self.metadata = []
            
            metadata_path = os.path.join(self.db_path, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            index_path = os.path.join(self.db_path, "faiss.index")
            faiss.write_index(self.index, index_path)
            
            return True
        except Exception as e:
            print(f"Ошибка при очистке базы данных: {e}")
            return False
    
    def get_stats(self):
        try:
            return {
                "total_records": len(self.metadata),
                "dimension": self.dimension,
                "directory": self.db_path
            }
        except Exception as e:
            print(f"Ошибка при получении статистики: {e}")
            return None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Log Analyzer")
        self.setMinimumSize(800, 600)
        
        load_dotenv()
        self.api_url = os.getenv('LLM_URL', 'http://localhost:8000/v1/chat/completions')
        self.api_key = os.getenv('API_KEY', '')
        
        self.statusBar = self.statusBar()
        self.statusBar.setStyleSheet("""
            QStatusBar {
                background-color: #f0f0f0;
                color: #333333;
                padding: 5px;
                font-size: 12px;
            }
        """)
        
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
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Здесь будут отображаться результаты анализа логов...")
        layout.addWidget(self.output_text)
        
        self.set_dark_theme()
        
        logger.debug("Главное окно инициализировано")
    
    def set_dark_theme(self):
        self.setStyleSheet("""
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
        """)
    
    def select_folder(self):
        folder_name = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку с логами",
            ""
        )
        
        if folder_name:
            self.current_folder = folder_name
            self.analyze_btn.setEnabled(True)
            self.output_text.setText(f"Выбрана папка: {folder_name}")
    
    def analyze_logs(self):
        if not hasattr(self, 'current_folder'):
            return
        
        self.select_folder_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.clear_db_btn.setEnabled(False)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.statusBar.showMessage("Обработка логов...")
        
        self.log_processor = LogProcessor(self.current_folder)
        self.log_processor.progress.connect(self.update_progress)
        self.log_processor.finished.connect(self.process_finished)
        self.log_processor.error.connect(self.process_error)
        self.log_processor.start()
    
    def update_progress(self, message):
        self.output_text.append(message)
        self.statusBar.showMessage(message)
    
    def process_finished(self, processed_logs):
        self.output_text.setText("Обработанные логи:\n\n" + processed_logs + "\n\nНачинаем анализ с помощью LLM...")
        self.statusBar.showMessage("Анализ с помощью LLM...")
        
        self.llm_analyzer = LLMAnalyzer(
            self.api_url,
            self.api_key,
            processed_logs,
            self.vectorizer
        )
        self.llm_analyzer.finished.connect(self.analysis_finished)
        self.llm_analyzer.error.connect(self.analysis_error)
        self.llm_analyzer.start()
    
    def analysis_finished(self, analysis):
        self.progress_bar.setVisible(False)
        
        self.select_folder_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.clear_db_btn.setEnabled(True)
        
        self.output_text.append("\n\nРезультаты анализа LLM:\n\n" + analysis)
        
        self.vectorizer.add_to_db(analysis)
        
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

def main():
    logger.debug("Запуск приложения")
    app = QApplication(sys.argv)
    
    window = MainWindow()
    
    window.show_loading()
    
    def init_vectorizer():
        window.vectorizer = Vectorizer()
        window.hide_loading()
        window.show()
    
    QTimer.singleShot(100, init_vectorizer)
    
    logger.debug("Приложение запущено")
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 