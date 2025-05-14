import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Поддерживаемые расширения файлов
SUPPORTED_EXTENSIONS = {
    '.log', '.txt', '.evtx', '.json', '.jsonl', '.csv',
    '.xml', '.yaml', '.yml', '.ini', '.conf', '.out',
    '.err', '.debug', '.trace', '.audit', '.syslog'
}

# Поддерживаемые архивы
SUPPORTED_ARCHIVES = {'.zip', '.gz', '.tar', '.rar'}

# Настройки среды
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE' 