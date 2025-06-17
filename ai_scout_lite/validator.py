"""Проверка адекватности пилотных проектов."""

from __future__ import annotations

from dataclasses import dataclass

#from langchain.llms import OpenAI
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate

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
    try:
        import json

        data = json.loads(result)
        return ValidationResult(
            acceptable=bool(data.get("acceptable")),
            reason=data.get("reason", ""),
        )
    except Exception:  # noqa: BLE001
        return ValidationResult(False, "parse error")

