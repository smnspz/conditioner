"""Run a matrix of fitness-level × readiness-profile scenarios and write results to a file.

Fitness levels tested: 2 (beginner), 5 (intermediate), 9 (advanced)
Readiness profiles tested: poor, moderate, good

Usage:
    poetry run python scripts/run_scenarios.py <access_token> [base_url] [output_file]

Defaults:
    base_url    http://localhost:9876
    output_file e2e_results.md
"""

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime

from e2e_flow import QuestionnaireAnswers, run


@dataclass
class Scenario:
    """A single test scenario combining a fitness level and a readiness profile.

    Attributes:
        name: Human-readable label for this scenario.
        fitness_level: Weekly self-reported fitness level, 1–10.
        questionnaire: Subjective readiness answers for today.
    """

    name: str
    fitness_level: int
    questionnaire: QuestionnaireAnswers


SCENARIOS = [
    Scenario(
        name="Beginner / Poor readiness",
        fitness_level=2,
        questionnaire=QuestionnaireAnswers(fatigue=8, soreness=7, stress=7, sleep_quality=2),
    ),
    Scenario(
        name="Beginner / Good readiness",
        fitness_level=2,
        questionnaire=QuestionnaireAnswers(fatigue=2, soreness=1, stress=2, sleep_quality=8),
    ),
    Scenario(
        name="Intermediate / Poor readiness",
        fitness_level=5,
        questionnaire=QuestionnaireAnswers(fatigue=7, soreness=6, stress=6, sleep_quality=3),
    ),
    Scenario(
        name="Intermediate / Good readiness",
        fitness_level=5,
        questionnaire=QuestionnaireAnswers(fatigue=2, soreness=2, stress=2, sleep_quality=8),
    ),
    Scenario(
        name="Advanced / Moderate readiness",
        fitness_level=9,
        questionnaire=QuestionnaireAnswers(fatigue=5, soreness=4, stress=5, sleep_quality=5),
    ),
    Scenario(
        name="Advanced / Good readiness",
        fitness_level=9,
        questionnaire=QuestionnaireAnswers(fatigue=1, soreness=1, stress=1, sleep_quality=9),
    ),
]


def _format_exercise(ex: dict) -> str:
    """Format a single block exercise entry."""

    name = ex.get("exercise_name", ex.get("exercise_id", "?"))
    sets = ex.get("sets", 1)
    reps = ex.get("reps")
    duration = ex.get("duration_seconds")
    cue = ex.get("intensity_cue", "")

    if reps is not None:
        detail = f"{sets}×{reps}"
    elif duration is not None:
        detail = f"{sets}×{duration}s"
    else:
        detail = f"{sets} sets"

    if cue:
        detail += f" ({cue})"

    # Return formatted exercise line
    return f"  - {name}: {detail}"


def _format_session(session: dict) -> str:
    """Format a single session for the results file."""

    lines = [f"  **{session['date']}**"]
    blocks = session.get("blocks", [])
    if not blocks:
        lines.append("  _(rest day)_")
        return "\n".join(lines)
    for block in blocks:
        block_type = block.get("type", "main").title()
        est = block.get("estimated_minutes", "?")
        lines.append(f"  _{block_type} (~{est} min)_")
        lines.extend(_format_exercise(ex) for ex in block.get("exercises", []))
    return "\n".join(lines)


def _format_result(scenario: Scenario, result: dict) -> str:
    """Format one scenario result as a Markdown section."""

    readiness = result["readiness"]
    workout = result["workout"]

    q = scenario.questionnaire
    lines = [
        f"## {scenario.name}",
        "",
        "### Inputs",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| Fitness level | {scenario.fitness_level}/10 |",
        f"| Fatigue | {q.fatigue}/10 |",
        f"| Soreness | {q.soreness}/10 |",
        f"| Stress | {q.stress}/10 |",
        f"| Sleep quality | {q.sleep_quality}/10 |",
        f"| Is sick | {'yes' if q.is_sick else 'no'} |",
        "",
        "### Computed readiness",
        f"**Score:** {readiness['score']}/100  ",
        f"**Zone:** {readiness['zone']}",
        "",
        "### Generated workout",
    ]
    for session in workout.get("sessions", []):
        lines.append(_format_session(session))
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


async def main(token: str, base_url: str, output_path: str) -> None:
    results_md = [
        "# E2E Scenario Results",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"Base URL: {base_url}",
        "",
        "---",
        "",
    ]

    raw_results = []

    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"\n{'='*60}")
        print(f"Scenario {i}/{len(SCENARIOS)}: {scenario.name}")
        print(f"  Fitness level: {scenario.fitness_level}/10")
        print(
            f"  Questionnaire: fatigue={scenario.questionnaire.fatigue}, "
            f"soreness={scenario.questionnaire.soreness}, "
            f"stress={scenario.questionnaire.stress}, "
            f"sleep_quality={scenario.questionnaire.sleep_quality}"
        )
        print(f"{'='*60}")

        try:
            result = await run(token, base_url, scenario.fitness_level, scenario.questionnaire)
            results_md.append(_format_result(scenario, result))
            raw_results.append({"scenario": scenario.name, **result})
            print(
                f"  Readiness: {result['readiness']['score']}/100 "
                f"({result['readiness']['zone']})"
            )
            session_count = len(result["workout"].get("sessions", []))
            print(f"  Generated {session_count} sessions")
        except SystemExit:
            error_block = f"## {scenario.name}\n\n**FAILED** — see terminal output.\n\n---\n\n"
            results_md.append(error_block)
            raw_results.append({"scenario": scenario.name, "error": "failed"})

    # Write Markdown results
    with open(output_path, "w") as f:
        f.write("\n".join(results_md))
    print(f"\nResults written to {output_path}")

    # Write raw JSON alongside for inspection
    json_path = output_path.replace(".md", ".json")
    with open(json_path, "w") as f:
        json.dump(raw_results, f, indent=2, default=str)
    print(f"Raw JSON written to {json_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    _token = sys.argv[1]
    _url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:9876"
    _output = sys.argv[3] if len(sys.argv) > 3 else "e2e_results.md"
    asyncio.run(main(_token, _url, _output))
