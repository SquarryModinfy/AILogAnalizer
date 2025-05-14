"""
Класс для обработки лог-файлов различных форматов
"""

import os
import json
import re
import zipfile
import tarfile
import rarfile
import tempfile
import win32evtlog
from multiprocessing import Pool, cpu_count
from PySide6.QtCore import QThread, Signal
from core.constants import logger, SUPPORTED_EXTENSIONS, SUPPORTED_ARCHIVES

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
        self.supported_extensions = SUPPORTED_EXTENSIONS
        self.supported_archives = SUPPORTED_ARCHIVES
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
            logger.debug(f"Запуск обработки для папки: {self.folder_path}")
            
            self.progress.emit(f"Поиск файлов в {self.folder_path}...")
            files_to_process = self.get_files_to_process(self.folder_path)
            
            if not files_to_process:
                return
            
            self.progress.emit(f"Найдено {len(files_to_process)} файлов для обработки")
            
            self.temp_dir = tempfile.mkdtemp()
            
            all_lines = []
            
            with Pool(processes=self.num_processes) as pool:
                results = []
                for file_path in files_to_process:
                    self.progress.emit(f"Обрабатываем файл: {os.path.basename(file_path)}")
                    args = (file_path, self.supported_extensions, self.supported_archives, self.temp_dir)
                    results.append(pool.apply_async(process_file_wrapper, (args,)))
                
                for result in results:
                    lines = result.get()
                    all_lines.extend(lines)
                    self.progress.emit(f"Обработано {len(lines)} строк")
            
            logger.debug(f"Обработано {len(all_lines)} строк")
            
            processed_text = "\n".join(all_lines)
            logger.debug("Обработка завершена")
            self.finished.emit(processed_text)
            
        except Exception as e:
            error_msg = f"Ошибка при обработке: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg) 