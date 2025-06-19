"""CLI вход в AI-Scout-Lite."""

from __future__ import annotations
from ai_scout_lite.discover import discover_org
import argparse
import os
from pathlib import Path

from ai_scout_lite import discover, cases, partners, pilots, validator




def main() -> None:

    parser = argparse.ArgumentParser(description="AI-Scout-Lite")
    #parser.add_argument("org_name", help="Название организации")
    parser.add_argument("org_name", help="Название организации", nargs="?", default="Сколтех")
    args = parser.parse_args()
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    discover_org(args.org_name, output_dir)

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

