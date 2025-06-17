"""Определение научных тем по публикациям и патентам."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

#from langchain.llms import OpenAI
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

PROMPT_TOPIC_NAME = """
Назови коротким заголовком (≤7 слов) научную проблему, которую решают
следующие публикации {titles} (список заголовков через \n). Дай один заголовок.
"""


@dataclass
class Topic:
    """Описание научной темы."""

    id: int  # порядковый номер темы
    name: str  # краткое название
    publications: List[str]  # исходные заголовки публикаций


def generate_topic_name(titles: List[str]) -> str:
    """Создаём название темы при помощи LLM."""
    llm = OpenAI(temperature=0)
    prompt = PromptTemplate(template=PROMPT_TOPIC_NAME, input_variables=["titles"])
    chain = LLMChain(prompt=prompt, llm=llm)
    return chain.run(titles="\n".join(titles))

