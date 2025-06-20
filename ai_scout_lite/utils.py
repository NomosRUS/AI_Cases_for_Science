# filename: ai_scout_lite/utils.py
"""Utility helpers for AI-Scout-Lite."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

def _to_text(obj: Any) -> str:
    """Преобразует вход в строку.

    • AIMessage / ChatMessage → берём .content
    • bytes → декодируем utf-8
    • всё остальное → str(obj)
    """
    if hasattr(obj, "content"):           # LangChain message
        return obj.content or ""
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="ignore")
    return str(obj)

def extract_json(text_or_msg: Any) -> Dict[str, Any]:
    """Извлекает **первый** JSON-объект из текста или LangChain-сообщения.

    Возвращает пустой dict, если блок не найден или парсинг не удался.
    """
    raw_text = _to_text(text_or_msg)

    match = re.search(r"\{.*?\}", raw_text, flags=re.DOTALL)
    if not match:
        logging.warning("No JSON object found in text")
        return {}

    try:
        return json.loads(match.group(0))
    except Exception as exc:           # noqa: BLE001
        logging.warning("Failed to parse JSON: %s", exc)
        return {}
