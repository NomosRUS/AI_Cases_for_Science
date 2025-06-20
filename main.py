"""CLI вход в AI-Scout-Lite."""

from __future__ import annotations

from ai_scout_lite.discover import discover_org
import argparse
from pathlib import Path
import time                 # ← добавьте
import random

from ai_scout_lite import discover, cases, partners, pilots, validator

ORG_NAMES = [
        "Институт металлоорганической химии им. Г.А. Разуваева",
        #"Институт катализа им. Г.К. Борескова",
        #"ФЕДЕРАЛЬНОЕ ГОСУДАРСТВЕННОЕ БЮДЖЕТНОЕ УЧРЕЖДЕНИЕ НАУКИ ПЕРМСКИЙ ФЕДЕРАЛЬНЫЙ ИССЛЕДОВАТЕЛЬСКИЙ ЦЕНТР "
        #"УРАЛЬСКОГО ОТДЕЛЕНИЯ РОССИЙСКОЙ АКАДЕМИИ НАУК"
        # добавьте сколько нужно
    ]

def main() -> None:
    """
    Запускает discover-пайплайн для всех организаций из ORG_NAMES.
    Опционально можно передать --org-file <txt>, чтобы читать список из файла (там же где main.py -
    "C:/Users/Me/Docs/orgs.txt").
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--org-file",
        help="Путь к .txt/.csv со списком организаций (по одной строке)",
    )
    parser.add_argument(
        "--out",
        default="output",
        help="Каталог, куда складываются результаты",
    )
    args = parser.parse_args()

    # ── откуда берём список организаций ───────────────────────────────
    org_list = ORG_NAMES
    if args.org_file:                               # если указан файл
        with open(args.org_file, encoding="utf-8") as fh:
            org_list = [line.strip() for line in fh if line.strip()]

    output_root = Path(args.out)
    output_root.mkdir(exist_ok=True)

    # ── основной цикл ─────────────────────────────────────────────────
    for org in org_list:
        discover_org(org, output_root / org.replace(" ", "_"))
        # «честная» пауза, чтобы не ловить ratelimit DDG
        time.sleep(3 + random.uniform(0, 2))


    # console.print("[bold]Ищем AI-кейсы...")
    # cases_df = cases.gather_ai_cases(args.org_name, insights.tasks)
    # cases_df.to_csv(output_dir / "ai_cases.csv", index=False)
    #
    # console.print("[bold]Ищем партнёров...")
    # partners_df = partners.find_partners(args.org_name)
    # partners_df.to_csv(output_dir / "partners.csv", index=False)
    #
    # console.print("[bold]Генерируем пилотные проекты...")
    # pilots_md = output_dir / "pilot_ideas.md"
    # with pilots_md.open("w", encoding="utf-8") as f:
    #     for i, task in enumerate(insights.tasks[:3]):
    #         case_task = cases_df.task.iloc[i] if i < len(cases_df) else ""
    #         partner = partners_df.name.iloc[0] if not partners_df.empty else ""
    #         pilot = pilots.generate_pilot(args.org_name, task, case_task, partner)
    #         validation = validator.validate_pilot(pilot.title + "\n" + pilot.body)
    #         status = "OK" if validation.acceptable else f"НЕ ПОДХОДИТ: {validation.reason}"
    #         f.write(f"## {pilot.title}\n{pilot.body}\n**Validation:** {status}\n\n")


if __name__ == "__main__":
    main()

