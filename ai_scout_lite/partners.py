"""Поиск индустриальных партнёров организации."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import List

import pandas as pd
from duckduckgo_search import DDGS
import requests_cache

requests_cache.install_cache("ai_scout_cache")


@dataclass
class Partner:
    """Информация о партнёре."""

    name: str
    sector: str
    evidence_link: str


def search_duckduckgo(query: str, max_results: int = 10) -> List[str]:
    """Поиск ссылок. TODO: заменить на Perplexity API."""
    links: List[str] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            if r.get("href"):
                links.append(r["href"])
    return links


def find_partners(org: str, max_results: int = 5) -> pd.DataFrame:
    """Ищем упоминания индустриальных партнёров."""
    partners: List[Partner] = []
    for url in search_duckduckgo(f"{org} industrial partner", max_results=max_results):
        name = urllib.parse.urlparse(url).netloc.split(".")[0]
        partners.append(Partner(name=name.capitalize(), sector="", evidence_link=url))
    return pd.DataFrame([p.__dict__ for p in partners])

