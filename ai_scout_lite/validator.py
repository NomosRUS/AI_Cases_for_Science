"""Проверка адекватности пилотных проектов."""

from __future__ import annotations

from dataclasses import dataclass
import logging

# from langchain.llms import OpenAI
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate

from .utils import extract_json

PROMPT_VALIDATION = """
Оцени, удовлетворяет ли пилотный проект {pilot} критериям:
1) повышает эффективность научной работы организации,
2) решает актуальную научную задачу,
3) релевантен интересам указанных партнёров.
Ответ JSON {{ "acceptable": bool, "reason": "" }}.
"""


@dataclass
class ValidationResult:
    """Результат проверки."""

    acceptable: bool  # прошёл ли пилот проверку
    reason: str  # аргументация решения


def validate_pilot(pilot_text: str) -> ValidationResult:
    """Запрос к LLM для оценки пилотного проекта."""
    llm = OpenAI(temperature=0)
    prompt = PromptTemplate(template=PROMPT_VALIDATION, input_variables=["pilot"])
    chain = prompt | llm
    result = chain.invoke({"pilot": pilot_text})  # ответ LLM
    data = extract_json(result)
    if data:
        return ValidationResult(
            acceptable=bool(data.get("acceptable")),
            reason=data.get("reason", ""),
        )
    logging.warning("Failed to parse validation result")
    return ValidationResult(False, "parse error")
