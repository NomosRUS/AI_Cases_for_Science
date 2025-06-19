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

import json
import logging
import os
import urllib.parse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

try:
    from rich.console import Console
except Exception:  # pragma: no cover - rich is optional
    class Console:
        def print(self, *args, **kwargs):  # type: ignore[no-redef]
            print(*args)

from duckduckgo_search import DDGS
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
import requests_cache
import trafilatura

from .utils import extract_json

# cache web requests to speed up repeated runs
requests_cache.install_cache("ai_scout_cache")

console = Console()


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
Ответ JSON:
{"activities": [...], "results": [...], "research": [...], "partners": [...]}
"""


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------

def search_duckduckgo(query: str, max_results: int = 10) -> List[str]:
    """Return a list of links for the query from DuckDuckGo."""

    links: List[str] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            if r.get("href"):
                links.append(r["href"])
    return links


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

def _extract_info(text: str) -> OrgInfo:
    """Use LLM to extract structured info from raw text."""

    llm = OpenAI(temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY", "OPENAI_API_KEY"))
    prompt = PromptTemplate(template=PROMPT_INFO, input_variables=["text"])
    chain = prompt | llm
    result = chain.invoke({"text": text[:4000]})
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

def find_official_site(org: str) -> str:
    """Try to find the official site of the organisation."""

    for url in search_duckduckgo(f"{org} официальный сайт", max_results=5):
        domain = urllib.parse.urlparse(url).netloc.lower()
        if org.split()[0].lower() in domain:
            return url
    return ""


def extract_official_info(org: str) -> OrgInfo:
    """Collect information from the organisation's official site."""

    url = find_official_site(org)
    if not url:
        logging.warning("Official site for %s not found", org)
        return OrgInfo([], [], [], [])

    console.print(f"[bold]Читаем официальный сайт {url}")
    text = fetch_text(url)
    return _extract_info(text)


# ---------------------------------------------------------------------------
# internet search
# ---------------------------------------------------------------------------

def gather_internet_info(org: str, max_results: int = 5) -> OrgInfo:
    """Search the web for public information about the organisation."""

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

    output_dir.mkdir(parents=True, exist_ok=True)

    site_info = extract_official_info(org)
    web_info = gather_internet_info(org)

    save_json(site_info, output_dir / "site_info.json")
    save_json(web_info, output_dir / "internet_info.json")

    save_txt(site_info, output_dir / "site_info.txt")
    save_txt(web_info, output_dir / "internet_info.txt")

