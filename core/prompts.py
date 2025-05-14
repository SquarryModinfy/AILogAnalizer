"""
Промпты для работы с LLM моделями
"""

import os
from dotenv import load_dotenv
from core.constants import logger

# Загружаем переменные окружения 
load_dotenv()

# Стандартный промпт для анализа логов, используется если пользовательский не настроен
DEFAULT_LOG_ANALYSIS_PROMPT = """Проанализируй следующие логи. Предоставь:
1. Краткое описание проблемы
2. Возможные причины
3. Рекомендации по исправлению

Текущие логи:
{current_logs}

Похожие логи:
{similar_logs}
"""

# Получаем пользовательский промпт из переменной среды или используем стандартный
user_prompt_raw = os.getenv('LLM_PROMPT', '')

# Преобразуем экранированные переносы строк обратно в реальные
if user_prompt_raw:
    try:
        USER_PROMPT = user_prompt_raw.replace('\\n', '\n')
        logger.debug(f"Загружен пользовательский промпт, длина: {len(USER_PROMPT)}")
    except Exception as e:
        logger.error(f"Ошибка при обработке пользовательского промпта: {str(e)}")
        USER_PROMPT = DEFAULT_LOG_ANALYSIS_PROMPT
else:
    USER_PROMPT = DEFAULT_LOG_ANALYSIS_PROMPT

# Промпт для анализа логов (может быть изменен пользователем)
LOG_ANALYSIS_PROMPT = USER_PROMPT 