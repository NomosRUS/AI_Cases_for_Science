"""Поиск и отбор AI-кейсов."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
from duckduckgo_search import DDGS
from langchain.chains import LLMChain
from langchain_openai import OpenAI
#from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
import requests_cache
import trafilatura

PROMPT_CASE_FILTER = """
Определи, описывает ли текст веб-страницы {text} успешный кейс применения
искусственного интеллекта в научных исследованиях.
Ответ JSON: {{ "is_ai_case": bool, "task": "", "ai_method": "", "kpi": "" }}
"""

requests_cache.install_cache("ai_scout_cache")


def search_duckduckgo(query: str, max_results: int = 10) -> List[str]:
    """Простой поиск ссылок. TODO: заменить на Perplexity API."""
    links: List[str] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            if r.get("href"):
                links.append(r["href"])
    return links


@dataclass
class AICase:
    """Структура для данных по AI-кейсу."""

    topic_id: int  # индекс соответствующей научной задачи
    task: str  # формулировка задачи
    org: str  # название организации
    ai_method: str  # применённый метод ИИ
    kpi: str  # показатель эффективности
    url: str  # ссылка на источник


def analyze_url(url: str, topic_id: int, org: str) -> Optional[AICase]:
    """Анализируем страницу на предмет AI-кейса."""
    try:
        html = trafilatura.fetch_url(url)
        if not html:
            return None
        text = trafilatura.extract(html) or ""
    except Exception as exc:  # noqa: BLE001
        logging.warning("Failed to fetch case %s: %s", url, exc)
        return None

    llm = OpenAI(temperature=0)
    prompt = PromptTemplate(template=PROMPT_CASE_FILTER, input_variables=["text"])
    chain = LLMChain(prompt=prompt, llm=llm)
    result = chain.run(text=text[:4000])  # ответ от LLM

    try:
        import json

        data = json.loads(result)
        if data.get("is_ai_case"):
            return AICase(
                topic_id=topic_id,
                task=data.get("task", ""),
                org=org,
                ai_method=data.get("ai_method", ""),
                kpi=data.get("kpi", ""),
                url=url,
            )
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to parse LLM result for %s: %s", url, exc)
    return None


def gather_ai_cases(org: str, tasks: List[str], max_results: int = 5) -> pd.DataFrame:
    """Ищем AI-кейсы, относящиеся к задачам."""
    cases: List[AICase] = []
    for i, task in enumerate(tasks):
        query = f"{org} {task} AI case study"  # поисковый запрос
        for url in search_duckduckgo(query, max_results=max_results):
            case = analyze_url(url, topic_id=i, org=org)
            if case:
                cases.append(case)
    return pd.DataFrame([c.__dict__ for c in cases])

