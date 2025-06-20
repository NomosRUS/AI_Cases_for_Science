"""Utilities for discovering information about an organisation.

The module performs five operations:
1. Find the official web site of an organisation by name.
2. Extract key facts from the official web site: activities, 2022-2025 results,
   research directions and partners.
3. Search the internet and collect the same information from public sources.
4. Store data from steps 2 and 3 in separate JSON files.
5. Save human readable summaries from steps 2 and 3 in two txt files.
"""



from __future__ import annotations
import itertools


from rich import box, table
from readability import Document
from bs4 import BeautifulSoup as BS

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

from urllib.parse import quote_plus
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


from fake_useragent import UserAgent
import json
import logging
import os
import urllib.parse
from dataclasses import dataclass, asdict
from pathlib import Path

import re, urllib.parse, tldextract, requests
from transliterate import translit
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import requests_cache
import trafilatura
from .utils import extract_json
from typing import Sequence

# cache web requests to speed up repeated runs
requests_cache.install_cache("ai_scout_cache")

import time
import random
from typing import List
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException
from rich.console import Console

if os.getenv("OPENAI_API_KEY"):
    print("OPENAI_API_KEY настроена")
else:
    print("Переменная OPENAI_API_KEY не задана")

console = Console()

# Реальный Firefox UA (июнь-2025)
FIREFOX_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
    "Gecko/20100101 Firefox/126.0"
)
HEADERS = {
    "User-Agent": FIREFOX_UA,
    "Accept":
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru,en;q=0.9",
    "DNT": "1",
}
OUTPUT_ROOT = Path("output")
GOOD_TLDS = {"ru", "su", "org", "edu", "ac", "science", "tech"}
_MAX_RETRIES = 3          # сколько раз пробуем прежде чем сдаться
_BASE_SLEEP  = 2          # базовая задержка (сек)


@dataclass
class OrgInfo:
    """Structured information about an organisation."""

    activities: List[str]
    results: List[str]
    research: List[str]
    partners: List[str]


PROMPT_INFO = """
Ты ассоциируешься с научной аналитикой. Проанализируй текст {text} и
выдели:
1. основные направления деятельности организации,
2. основные результаты за 2022-2025 годы,
3. основные научные направления организации,
4. ключевых партнёров организации.
Верни **строго JSON**:
{{"activities": [...], "results": [...], "research": [...], "partners": [...]}}
"""


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------


def search_duckduckgo(query: str, max_results: int = 2) -> List[str]:
    """DuckDuckGo search with Firefox UA, back-off and verbose logging."""
    console.print(f"[cyan]→ DuckDuckGo query:[/] {query}")

    for attempt in range(3):                    # ≤ 3 попытки
        try:
            with DDGS(headers=HEADERS, timeout=15) as ddgs:
                hits = [
                    r["href"] for r in ddgs.text(query, max_results=max_results)
                    if r.get("href")
                ]

            if hits:
                console.print(
                    "[green]✔ результаты:[/]\n  " + "\n  ".join(hits[:2])
                )
            else:
                console.print("[yellow]⚠ ничего не найдено[/]")

            return hits

        except DuckDuckGoSearchException as err:
            wait = (2 ** attempt) + random.uniform(0, 1.2)
            console.print(
                f"[yellow]⚠ Rate-limit:[/] {err}. "
                f"Повтор через {wait:0.1f} с."
            )
            time.sleep(wait)

    console.print("[red]❌ DuckDuckGo: все попытки исчерпаны[/]")
    return []

def ddg_first_links_firefox(query: str, n: int = 3) -> list[str]:
    """
    Возвращает первые n ссылок DuckDuckGo через headless-Firefox.
    • Не кликает форму; сразу открывает URL вида `/?q=...&ia=web`.
    • Ждёт до 7 с появления результатов и берёт ссылки по CSS `.result__a`.
    """
    console.print(f"[cyan]→ Firefox DDG query:[/] {query}")

    options = Options()
    options.headless = True
    driver = webdriver.Firefox(
        service=Service(GeckoDriverManager().install()),
        options=options,
    )

    try:
        url = (
            "https://duckduckgo.com/?q="
            + quote_plus(query)
            + "&ia=web&kl=ru-ru"
        )
        driver.get(url)

        try:
            WebDriverWait(driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.result__a"))
            )
        except TimeoutException:
            console.print("[yellow]⚠ DDG: результаты не появились за 7 с[/]")
            return []

        links = driver.find_elements(By.CSS_SELECTOR, "a.result__a")[: n]
        hrefs = [link.get_attribute("href") for link in links]

        if hrefs:
            console.print(
                "[green]✔ результаты:[/]\n  " + "\n  ".join(hrefs)
            )
        else:
            console.print("[yellow]⚠ ничего не найдено[/]")

        return hrefs

    finally:
        driver.quit()


def fetch_text(url: str) -> str:
    """Download and clean page text."""

    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded) or ""
    except Exception as exc:  # noqa: BLE001
        logging.warning("Failed to fetch %s: %s", url, exc)
    return ""


# ---------------------------------------------------------------------------
# information extraction
# ---------------------------------------------------------------------------

def _extract_info(text: str, model: str = "gpt-4o-mini") -> OrgInfo:
    """
    Извлекает структурированную информацию о научной организации с помощью LLM.

    Args:
        text: сырой объединённый текст (About, новости, публикации).
        model: имя модели OpenAI Chat-Completion API (по умолчанию gpt-4o-mini).

    Returns:
        OrgInfo dataclass с четырьмя списками строк.
    """
    console.print("[bold cyan]⏳  Извлекаем ключевую информацию из текста…")

    # 1. Создаём чат-LLM
    llm = ChatOpenAI(
        model=model,
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),  # без дефолта-плацебо!
    )

    # 2. Готовим чат-шаблон
    prompt = ChatPromptTemplate.from_template(PROMPT_INFO)
    print(prompt.format(text="demo"))

    # 3. Запускаем цепочку (Prompt → ChatOpenAI)
    chain = prompt | llm
    result = chain.invoke({"text": text[:4000]})  # ≤4 000 символов для экономии

    # 4. JSON-парсинг + формирование dataclass
    data = extract_json(result)
    return OrgInfo(
        activities=data.get("activities", []),
        results=data.get("results", []),
        research=data.get("research", []),
        partners=data.get("partners", []),
    )

# ---------------------------------------------------------------------------
# official web site
# ---------------------------------------------------------------------------

def _clean_name(name: str) -> str:
    """Убираем юр.формы / кавычки, оставляя «суть»."""
    return re.sub(
        r"(ФГБУ|ФИЦ|НИИ|АО|ФГУП|им\..*|\".*?\"|[«»])",
        "",
        name,
        flags=re.I
    ).strip()


def _looks_like_official(url: str, clean: str, abbr: str) -> bool:
    """Эвристика: домен не wiki/справочник + содержит аббревиатуру
    или любую латинизированную часть названия."""
    host = urllib.parse.urlparse(url).netloc.lower()

    if host.startswith("ru.wikipedia.org") or host.endswith(".wikipedia.org"):
        return False

    # латинизируем первое содержательное слово (Institute → institute, Институт → institut)
    first_word = translit(clean.split()[0], 'ru', reversed=True).lower()

    return (
        first_word in host
        or abbr.lower() in host              # РАН → ran, ИНХ → inh и т.п.
        or "ras." in host                    # большинство сайтов РАН
    )


def find_official_site(org: str) -> str:
    """Возвращает URL официального сайта либо ''."""
    console.rule("[bold green]🔍 Поиск официального сайта")
    clean = _clean_name(org)
    abbr  = "".join(w[0] for w in clean.split() if len(w) > 2)

    queries = [
        f"{clean} официальный сайт",
        f"{clean} сайт",
        f"{translit(clean, 'ru', reversed=True)} official website",
        f"{abbr} сайт" if len(abbr) > 3 else "",
    ]

    for q in queries:
        if not q:
            continue

        # ПРИОРИТЕТ — headless Firefox (без ratelimit)
        for url in ddg_first_links_firefox(q, n=4):
            if _looks_like_official(url, clean, abbr):
                console.print(f"[green]✔ официальный сайт найден:[/] {url}")
                return url

        # fallback на duckduckgo_search (быстрее, но с риском 202)
        for url in search_duckduckgo(q, max_results=2):
            if _looks_like_official(url, clean, abbr):
                console.print(f"[green]✔ официальный сайт найден:[/] {url}")
                return url

        time.sleep(1)  # честная пауза перед следующей фразой

    console.print("[yellow]⚠ официальный сайт не найден")
    return ""



def extract_official_info(org: str) -> OrgInfo:
    """
    1) ищет официальный сайт;
    2) скачивает и чистит текст (через _diagnostic_download);
    3) пишет raw-текст в output/<org>/site_info.txt, если он не пустой;
    4) отдаёт структурированную OrgInfo (или «пустую», если сайта нет).
    """
    url = find_official_site(org)
    if not url:
        logging.warning("Official site for %s not found", org)
        return OrgInfo([], [], [], [])

    console.print(f"[bold]Читаем официальный сайт: {url}")
    text = _diagnostic_download(url)            # ← новый helper

    # ── сохраняем только, если хоть что-то извлекли ─────────────────
    if text and len(text) >= 500:
        org_dir = OUTPUT_ROOT / org.replace(" ", "_")
        org_dir.mkdir(parents=True, exist_ok=True)
        (org_dir / "site_info.txt").write_text(text, encoding="utf-8")
        console.print(f"[green]📝 site_info.txt записан ({len(text)} симв.)")
    else:
        console.print("[yellow]⚠ текст пуст — файл не создан")

    return _extract_info(text)

# ---------------------------------------------------------------------------
# internet search
# ---------------------------------------------------------------------------

def gather_internet_info(org: str, max_results: int = 5) -> OrgInfo:
    """Search the web for public information about the organisation."""
    console.print("Читаем иные открытые источники")

    texts: List[str] = []
    query = f"{org} результаты 2022 2025"
    for url in search_duckduckgo(query, max_results=max_results):
        txt = fetch_text(url)
        if txt:
            texts.append(txt)
    return _extract_info("\n".join(texts))


# ---------------------------------------------------------------------------
# saving helpers
# ---------------------------------------------------------------------------

def save_json(info: OrgInfo, path: Path) -> None:
    path.write_text(json.dumps(asdict(info), ensure_ascii=False, indent=2), encoding="utf-8")
    console.print("сохранили файл")

def info_as_text(info: OrgInfo) -> str:
    lines = ["# Основные направления деятельности:"]
    lines += [f"- {a}" for a in info.activities]
    lines.append("\n# Основные результаты 2022-2025:")
    lines += [f"- {r}" for r in info.results]
    lines.append("\n# Научные направления:")
    lines += [f"- {s}" for s in info.research]
    lines.append("\n# Партнёры:")
    lines += [f"- {p}" for p in info.partners]
    return "\n".join(lines)


def save_txt(info: OrgInfo, path: Path) -> None:
    path.write_text(info_as_text(info), encoding="utf-8")


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def discover_org(org: str, output_dir: Path) -> None:
    """Run discovery pipeline for the organisation."""
    console.print("Запустили информационный скрининг организации")
    output_dir.mkdir(parents=True, exist_ok=True)

    site_info = extract_official_info(org)
    web_info = gather_internet_info(org)

    save_json(site_info, output_dir / "site_info.json")
    save_json(web_info, output_dir / "internet_info.json")

    save_txt(site_info, output_dir / "site_info.txt")
    save_txt(web_info, output_dir / "internet_info.txt")

def _diagnostic_download(url: str) -> str:
    """Скачивает URL, подробно логирует шаги, возвращает чистый текст ('' если нет)."""
    console.rule(f"[bold blue]🌐 Скачиваем {url}")
    headers = {"User-Agent": FIREFOX_UA}

    # ── 1. HTTP GET ───────────────────────────────────────────────────
    try:
        r = requests.get(url, headers=headers, timeout=20)
        console.print(f"Status: {r.status_code}, bytes: {len(r.content)}")
        r.raise_for_status()
    except requests.RequestException as err:
        console.print(f"[red]HTTP error:[/] {err}")
        return ""

    # ── 2. Кодировка ─────────────────────────────────────────────────
    enc_before = r.encoding or "None"
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding
    console.print(f"Encoding: {enc_before} → {r.encoding}")

    html = r.text

    # ── 3. Trafilatura ───────────────────────────────────────────────
    console.print("• Trafilatura.extract() …")
    text = trafilatura.extract(
        html,
        include_images=False,
        include_tables=False,
        no_fallback=False,
        target_language="ru",
    )
    if text:
        console.print(f"[green]✔ Trafilatura OK:[/] {len(text)} chars")
        return text

    console.print("[yellow]Trafilatura вернула None – пробуем fallback Readability")

    # ── 4. Readability fallback ──────────────────────────────────────
    try:
        doc = Document(html)
        text = BS(doc.summary(), "lxml").get_text(" ", strip=True)
        console.print(f"[green]✔ Readability OK:[/] {len(text)} chars")
        return text
    except Exception as err:
        console.print(f"[red]Readability failed:[/] {err}")
        return ""