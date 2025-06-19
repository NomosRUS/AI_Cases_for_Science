"""Модуль для веб-поиска и сбора текстов об организации."""

from __future__ import annotations

try:
    from rich.console import Console
except ImportError:
    class Console:
        def print(self, *args, **kwargs):
            print(*args)


import logging
from dataclasses import dataclass
from typing import List

from .utils import extract_json

import requests_cache
from duckduckgo_search import DDGS

# from langchain.llms import OpenAI
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
import trafilatura

# Включаем кэширование HTTP-запросов
requests_cache.install_cache("ai_scout_cache")

# Константы с промптами
PROMPT_SUMMARY = """
Ты аналитик научной деятельности. На основе собранной информации {text} выдели 5-7 научных достижений организации и
сформулируй 5 основных научных задач, которыми она занимается. Ответ JSON:
{{ "achievements": [...], "tasks": [...] }}
"""
console = Console()

def save_org_insights(org: str, output_dir: Path) -> discover.OrgInsights:
    """Собираем и сохраняем информацию об организации."""
    console.print(f"[bold]Собираем тексты об {org}...")
    texts = collect_org_texts(org)
    insights = summarize_org(texts)
    md_path = output_dir / "org_insights.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Достижения\n")
        for ach in insights.achievements:
            f.write(f"- {ach}\n")
        f.write("\n# Задачи\n")
        for task in insights.tasks:
            f.write(f"- {task}\n")
    return insights



def search_duckduckgo(query: str, max_results: int = 10) -> List[str]:
    """Ищем ссылки через DuckDuckGo. TODO: заменить на Perplexity API."""
    results: List[str] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            if r.get("href"):
                results.append(r["href"])
    return results


def fetch_text(url: str) -> str:
    """Скачиваем и очищаем текст страницы."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded) or ""
    except Exception as exc:  # noqa: BLE001
        logging.warning("Failed to fetch %s: %s", url, exc)
    return ""


def collect_org_texts(org: str, max_pages: int = 5) -> List[str]:
    """Собираем тексты с сайта организации."""
    texts: List[str] = []
    for url in search_duckduckgo(f"{org} science news", max_results=max_pages):
        text = fetch_text(url)
        if text:
            texts.append(text)
    return texts


@dataclass
class OrgInsights:
    """Сводная информация об организации."""

    achievements: List[str]  # ключевые достижения организации
    tasks: List[str]  # основные научные задачи


def summarize_org(texts: List[str]) -> OrgInsights:
    """Получаем список достижений и задач с помощью LLM."""
    llm = OpenAI(
        temperature=0,
        openai_api_key="OPENAI_API_KEY",
    )
    prompt = PromptTemplate(template=PROMPT_SUMMARY, input_variables=["text"])
    chain = prompt | llm
    joined = "\n".join(texts)[:4000]  # объединяем тексты и ограничиваем длину
    result = chain.invoke({"text": joined})  # запрос к LLM с текстом
    data = extract_json(result)
    if data:
        return OrgInsights(
            achievements=data.get("achievements", []),
            tasks=data.get("tasks", []),
        )
    return OrgInsights([], [])
