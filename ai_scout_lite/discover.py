"""Модуль для веб-поиска и сбора текстов об организации."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

import requests_cache
from duckduckgo_search import DDGS
#from langchain.llms import OpenAI
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import trafilatura

# Включаем кэширование HTTP-запросов
requests_cache.install_cache("ai_scout_cache")

# Константы с промптами
PROMPT_SUMMARY = """
Ты аналитик научной деятельности. На основе собранной информации, текста выдели 5-7 научных достижений организации и
сформулируй 5 основных научных задач, которыми она занимается. Ответ JSON:
{{ "achievements":[...], "tasks":[...] }}
"""


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

    achievements: List[str]
    tasks: List[str]


def summarize_org(texts: List[str]) -> OrgInsights:
    """Получаем список достижений и задач с помощью LLM."""
    llm = OpenAI(temperature=0, openai_api_key=
    "sk-proj-dphTObv3lmCT1loQNX8T9pj0vS_KKgSq46D-1fbc0QTJkZ5yIFy_CIgkzq0umYRkLE92wQc7a4T3BlbkFJydrUMqoUe8sDfUhHv4lrEn9e"
    "7M_As3Gy0vyDG4RGw4rwYI-EsqZ0Sg0X7nxtHqWgerqyB7K68A"
    )
    prompt = PromptTemplate(template=PROMPT_SUMMARY, input_variables=["text"])
    chain = LLMChain(prompt=prompt, llm=llm)
    joined = "\n".join(texts)[:4000]
    result = chain.run(text=joined)
    try:
        import json

        data = json.loads(result)
        return OrgInsights(achievements=data.get("achievements", []), tasks=data.get("tasks", []))
    except Exception as exc:  # noqa: BLE001
        logging.error("LLM parsing failed: %s", exc)
    return OrgInsights([], [])

