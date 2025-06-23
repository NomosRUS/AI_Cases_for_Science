# cases_org.py
# ------------------------------------------------------------------------------
# Сканируем список организаций и получаем краткие AI-кейсы через Perplexity-Sonar
# ------------------------------------------------------------------------------
from __future__ import annotations
import csv, logging, pathlib
from typing import List

# ── наши модули ───────────────────────────────────────────────────────────────
from perplexity import ask_sonar, PerplexityError          # поиск (сырой ответ)
from ai_scout_lite.discover import _clean_name             # убираем юр. приставки

import chardet

ORG_FILE  = pathlib.Path("orgforresearch.txt")              # входной список
OUT_CSV   = pathlib.Path("ai_cases_org.csv")                # итоговый CSV
MAX_TOKENS = 600                                            # длина ответа Sonar


def _build_prompt(org_clean: str) -> str:
    """Запрос в точности по вашему шаблону, только имя организации подставляем."""
    return (
        f"Какие кейсы внедрения и применения ИИ есть у {org_clean}. "
        "Выведи информацию только о найденных кейсах, включая описание решаемой "
        "научной задачи, полученных результатов, партнёров с которыми "
        "реализовывался кейс и роли партнёров. Результат выведи очень кратко. "
        "Если информации нет, строго напиши что информация "
        "в открытых источниках отсутствует."
    )


def _read_org_list(path: pathlib.Path) -> List[str]:
    """Читаем список организаций, корректно определяя кодировку."""
    raw = path.read_bytes()

    # 1. пробуем UTF-8 напрямую
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        # 2. пробуем windows-1251
        try:
            text = raw.decode("cp1251")
        except UnicodeDecodeError:
            # 3. авто-детект последней надежды (chardet)
            enc = chardet.detect(raw)["encoding"] or "utf-8"
            text = raw.decode(enc, errors="replace")
            logging.warning("orgforresearch.txt: использована кодировка %s", enc)

    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def main() -> None:
    if not ORG_FILE.exists():
        logging.error("Файл %s не найден", ORG_FILE)
        return

    orgs = _read_org_list(ORG_FILE)
    if not orgs:
        logging.error("В %s нет ни одной организации", ORG_FILE)
        return

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(
            f,
            delimiter=';',  # разделитель – «;»
            quoting=csv.QUOTE_MINIMAL,  # кавычки только при необходимости
            escapechar='\\'  # экранируем " внутри поля
        )
        writer.writerow(["org", "case"])          # заголовок

        for raw in orgs:
            org_clean = _clean_name(raw)
            prompt    = _build_prompt(org_clean)

            try:
                answer = ask_sonar(prompt, max_tokens=MAX_TOKENS)
            except PerplexityError as err:
                logging.warning("❌ %s – %s", org_clean, err)
                answer = f"Ошибка поиска: {err}"

            writer.writerow([raw, answer])
            logging.info("✔ %s — добавлено", org_clean)

    logging.info("Готово: ответы сохранены в %s", OUT_CSV)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
