# filename: ai_scout_lite/utils.py
"""Utility helpers for AI-Scout-Lite."""
from __future__ import annotations


import json, json5, logging, re
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

# ai_scout_lite/utils.py
import json, json5, logging, re

def extract_json(msg) -> dict:
    """
    Достаёт 1-й JSON-блок из строки/AIMessage.
    • терпит ```json … ``` и trailing comma
    • возвращает {} при любой ошибке
    """
    # 0. превратим AIMessage → str
    if hasattr(msg, "content"):
        msg = msg.content

    # 1. уберём ```json … ``` / ``` … ```
    msg = re.sub(r"```(?:json)?|```", "", msg, flags=re.I).strip()

    # 2. берём ДЛИННЕЙШИЙ блок {...}
    match = max(re.findall(r"\{.*?\}", msg, re.S), key=len, default="")
    if not match:
        logging.warning("extract_json: no JSON found")
        return {}

    # 3. сначала обычный json, потом json5
    for parser in (json.loads, json5.loads):
        try:
            return parser(match)
        except Exception:
            continue

    logging.warning("extract_json: cannot parse JSON after json5 fallback")
    return {}
