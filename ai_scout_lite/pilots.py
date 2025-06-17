"""Генерация пилотных проектов."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from langchain.chains import LLMChain
from langchain_openai import OpenAI
#from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate

PROMPT_PILOT_GEN = """
Составь черновик пилотного проекта внедрения ИИ для организации «{org}».
Используй проблему: {{task}}; релевантный AI-кейс: {{case_task}};
индустриальный партнёр: {{partner}}. Формат:
 {{title}}
 • Problem: ...
 • AI Solution: ...
 • Partner: ...
 • Expected Impact: ...
"""


@dataclass
class PilotProject:
    """Описание пилотного проекта."""

    title: str
    body: str


def generate_pilot(org: str, task: str, case_task: str, partner: str) -> PilotProject:
    """Создаём текст пилотного проекта."""
    llm = OpenAI(temperature=0)
    prompt = PromptTemplate(
        template=PROMPT_PILOT_GEN,
        input_variables=["org", "task", "case_task", "partner"],
    )
    chain = LLMChain(prompt=prompt, llm=llm)
    text = chain.run(org=org, task=task, case_task=case_task, partner=partner)
    lines = text.split("\n", 1)
    title = lines[0].strip() if lines else "Пилот"
    body = lines[1].strip() if len(lines) > 1 else ""
    return PilotProject(title=title, body=body)

