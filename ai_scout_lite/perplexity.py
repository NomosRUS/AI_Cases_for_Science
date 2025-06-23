# perplexity.py  (минимальный Q→A для модели Sonar)

import os, httpx, logging, time
from typing import Dict, Any

_PPX_KEY  = os.getenv("PPX_API_KEY")          # кладём ключ сюда
_CHAT_URL = "https://api.perplexity.ai/chat/completions"
_BACKOFF  = (1, 2.5, 5)                       # секунды между повторами


class PerplexityError(RuntimeError):
    pass


def _post_ppx(json_payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    """Один POST к Perplexity-chat с back-off на 429/5xx."""
    headers = {
        "Authorization": f"Bearer {_PPX_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ai-scout-lite/0.1",
    }
    for wait in (0, *_BACKOFF):
        if wait:
            time.sleep(wait)
        try:
            r = httpx.post(_CHAT_URL, headers=headers,
                           json=json_payload, timeout=timeout)
        except httpx.RequestError as err:
            logging.warning("Perplexity network error: %s", err)
            continue

        if r.status_code == 200:
            return r.json()

        if r.status_code in (429, 502, 503):
            logging.warning("Perplexity %s – retry in %s s", r.status_code, wait or 1)
            continue

        raise PerplexityError(f"HTTP {r.status_code}: {r.text[:200]}")

    raise PerplexityError("Перепробовали все ретраи — ответа нет")


# ──────────────────────────────────────────────────────────────────────
def ask_sonar(question: str,
              model: str = "sonar",  # или 'sonar-medium-chat'
              max_tokens: int = 512) -> str:
    """
    Отправляет *один* текстовый вопрос модели Sonar и возвращает сырой ответ
    (строку).  Никакой JSON-структуризации внутри.
    """
    if not _PPX_KEY:
        raise PerplexityError("PPX_API_KEY не задан")

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": question}
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens
    }

    data = _post_ppx(payload)
    # Perplexity chat API возвращает {"choices":[{"message":{"content": ...}}]}
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise PerplexityError(f"Неожиданный формат ответа: {data}")


# ─────────────────── CLI-проверка ───────────────────
if __name__ == "__main__":
    import sys
    org = " ".join(sys.argv[1:]) or "Институт металлоорганической химии им. Г.А. Разуваева"
    question = (f"Какие кейсы внедрения и применения ИИ есть у {org}. "
                "Выведи информацию только о найденных кейсах, включая описание решаемой "
                "научной задачи, полученного результата, партнёров с которыми реализовывался "
                "кейс и роли партнёров. Результат выведи очень кратко. Добавь ссылки. "
                "Если информации нет, строго напиши, что информация отсутствует и ничего (даже ссылки) более не добавляй.")
    try:
        answer = ask_sonar(question)
        print(answer)
    except PerplexityError as err:
        logging.error(err)
