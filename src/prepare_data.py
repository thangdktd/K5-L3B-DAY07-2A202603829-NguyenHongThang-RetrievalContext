"""
Data preparation script for Day 07.
Converts 292 chunks (Config B) and 20 questions from Day 06,
and registers 4 unanswerable questions (2 DEV, 2 TEST) for Agent evaluation.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY6_DIR = Path("D:/VinUniAI/K5-L3B-Day06-2A202603829-DataIngestionEngineering")
DAY6_CHUNKS_FILE = DAY6_DIR / "starter/results/ingestion/8992321820d7309de6ec875b22411af0a50b4c679576f9237646c28a484ac7b8/chunks_B.jsonl"
DAY6_QUESTIONS_FILE = DAY6_DIR / "benchmark/questions.json"


def convert_chunk(c: dict) -> dict:
    return {
        "id": c.get("id", c.get("chunk_id")),
        "source_id": c.get("source_id", c.get("document_id")),
        "source": c.get("source"),
        "page": c.get("page"),
        "text": c.get("text"),
        "metadata": c.get("metadata", {}),
    }


def convert_question(q: dict) -> dict:
    gold = q.get("gold")
    if gold is None:
        gold = [{
            "source_id": q.get("gold_source_id"),
            "page": q.get("gold_page"),
            "evidence": q.get("evidence_quote"),
        }]
    result = {
        "id": q.get("id"),
        "split": q.get("split"),
        "question": q.get("question"),
        "gold": gold,
        "expected_answer": q.get("expected_answer"),
    }
    if "filter" in q:
        result["filter"] = q["filter"]
    return result


def get_unanswerable_questions() -> list[dict]:
    return [
        {
            "id": "q_unans_dev_01",
            "split": "dev",
            "question": "What is the procedure and calculation formula for adding R32 refrigerant when retrofitting the VRV IV+ heat recovery system?",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "The Daikin VRV IV+ (REYQ8~20+REMQ5U7Y1B) manual strictly mandates R410A only (page 4 warns against using any other substance) and does not provide any retrofit procedure or calculation formulas for R32 refrigerant."
        },
        {
            "id": "q_unans_dev_02",
            "split": "dev",
            "question": "What is the rated sound pressure level in decibels (dBA) for outdoor unit model REYQ14U7Y1B during standard cooling operation?",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "The manual describes qualitative acoustic symptoms (such as clicking sounds, gas flowing sounds, and tone changes in Section 8), but does not publish quantitative rated sound pressure levels (dBA) or sound power spectrum curves for any unit model."
        },
        {
            "id": "q_unans_test_01",
            "split": "test",
            "question": "What is the manufacturer suggested retail price (MSRP) in USD and standard factory delivery lead time for the REMQ5U7Y1B outdoor unit?",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "Manual 4P546222-1E is strictly an installation and operation technical guide; it contains no commercial pricing, MSRP lists, or delivery lead time data."
        },
        {
            "id": "q_unans_test_02",
            "split": "test",
            "question": "What is the manufacturer part number and maximum switching frequency of the main IGBT power module mounted on the inverter compressor PCB (A1P)?",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "While the manual references PCB A1P for field settings and external pushbuttons (BS1-BS3) in Section 16, internal semiconductor schematics, component part numbers, and IGBT switching frequency ratings are proprietary and omitted from this manual."
        }
    ]


def main():
    raise SystemExit("Retired writer: use src/build_final_benchmark.py; benchmark freeze is immutable")


if __name__ == '__main__':
    main()
