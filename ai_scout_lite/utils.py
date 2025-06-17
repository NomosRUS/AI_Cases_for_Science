"""Utility helpers for AI Scout Lite."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict


def extract_json(text: str) -> Dict[str, Any]:
    """Return first JSON object found in the given text.

    If no JSON block is found or parsing fails, an empty dict is returned.
    """
    match = re.search(r"{.*?}", text, flags=re.DOTALL)
    if not match:
        logging.warning("No JSON object found in text")
        return {}
    try:
        return json.loads(match.group(0))
    except Exception as exc:  # noqa: BLE001
        logging.warning("Failed to parse JSON: %s", exc)
        return {}
