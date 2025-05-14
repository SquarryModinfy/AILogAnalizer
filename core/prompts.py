import os
from dotenv import load_dotenv
from core.constants import logger

load_dotenv()

DEFAULT_LOG_ANALYSIS_PROMPT = """Проанализируй следующие логи. Предоставь:
1. Краткое описание проблемы
2. Возможные причины
3. Рекомендации по исправлению

Текущие логи:
{current_logs}

Похожие логи:
{similar_logs}
"""

user_prompt_raw = os.getenv('LLM_PROMPT', '')

if user_prompt_raw:
    try:
        USER_PROMPT = user_prompt_raw.replace('\\n', '\n')
        logger.debug(f"Загружен пользовательский промпт, длина: {len(USER_PROMPT)}")
    except Exception as e:
        logger.error(f"Ошибка при обработке пользовательского промпта: {str(e)}")
        USER_PROMPT = DEFAULT_LOG_ANALYSIS_PROMPT
else:
    USER_PROMPT = DEFAULT_LOG_ANALYSIS_PROMPT

LOG_ANALYSIS_PROMPT = USER_PROMPT 