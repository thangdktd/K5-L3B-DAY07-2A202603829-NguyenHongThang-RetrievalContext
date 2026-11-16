"""
Build and strictly validate Day 07 benchmark.
- 15 DEV answerable questions (from Day 06)
- 5 NEW TEST answerable questions (t01-t05, verified against PDF and chunks)
- 4 Unanswerable questions (2 DEV, 2 TEST)
- Total: 24 benchmark questions (17 DEV, 7 TEST).
"""
import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
from baseline import hit, validate, normalize_text

DAY6_QUESTIONS_FILE = Path("D:/VinUniAI/K5-L3B-Day06-2A202603829-DataIngestionEngineering/benchmark/questions.json")

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def build():
    chunks = json.loads((ROOT / "data/chunks.json").read_text(encoding="utf-8"))
    assert len(chunks) == 292, f"Expected 292 chunks, got {len(chunks)}"

    # 1. 15 DEV answerable questions (Day 06 q01-q15)
    day6_raw = json.loads((ROOT / 'data/questions_day6_raw.json').read_text(encoding='utf-8'))
    dev_source = [q for q in day6_raw if q["split"] == "dev"]
    assert len(dev_source) == 15

    dev_questions = []
    for q in dev_source:
        gold = q.get('gold')
        if gold is None:
            gold = [{
                'source_id': q['gold_source_id'],
                'page': q['gold_page'],
                'evidence': q['evidence_quote']
            }]
        
        # Specific adjustments for table split cases in Strategy B
        if q['id'] == 'q11':
            # Minimum circuit ampacity and recommended fuses row for REYQ10 on page 29
            gold = [{
                'source_id': q['gold_source_id'],
                'page': 29,
                'evidence': 'REYQ10 22.0 A 25 A'
            }]
        elif q['id'] == 'q12':
            # Mode 1 and Mode 2 field setting definitions on page 32
            gold = [
                {
                    'source_id': q['gold_source_id'],
                    'page': 32,
                    'evidence': 'Mode 1 (monitoring settings) Mode 1 can be used to monitor the current situation of the outdoor unit. Some field setting contents can be monitored as well.'
                },
                {
                    'source_id': q['gold_source_id'],
                    'page': 32,
                    'evidence': 'Mode 2 is used to change the field settings of the system. Consulting the current field setting value and changing the current field setting value is possible.'
                }
            ]
        
        item = {
            'id': q['id'],
            'split': 'dev',
            'category': q.get('category', 'operation_limits'),
            'type': q.get('type', 'truc_tiep'),
            'question': q['question'],
            'gold': gold,
            'expected_answer': q['expected_answer']
        }
        if q['id'] == 'q12':
            item['gold_groups'] = [[g] for g in item.pop('gold')]
        if 'filter' in q:
            item['filter'] = q['filter']
        dev_questions.append(item)

    # 2. 5 NEW TEST answerable questions (t01-t05)
    test_questions = [
        {
            'id': 't01',
            'split': 'test',
            'category': 'operation_limits',
            'type': 'truc_tiep',
            'question': 'According to user safety instructions in section 3, why must a phase advancing capacitor NOT be installed on this unit?',
            'expected_answer': 'Because the unit is equipped with an inverter, and a phase advancing capacitor will reduce performance and may cause accidents.',
            'gold': [{
                'source_id': 'daikin_vrv_ivplus_4p546222_1e_2025_11',
                'page': 4,
                'evidence': 'Do NOT install a phase advancing capacitor, because this unit is equipped with an inverter. A phase advancing capacitor will reduce performance and may cause accidents.'
            }]
        },
        {
            'id': 't02',
            'split': 'test',
            'category': 'installation_piping',
            'type': 'truc_tiep',
            'question': 'According to section 11.4, what problem may occur if the outdoor unit is operated with the transportation stay attached?',
            'expected_answer': 'Abnormal vibration or noise may be generated.',
            'gold': [{
                'source_id': 'daikin_vrv_ivplus_4p546222_1e_2025_11',
                'page': 13,
                'evidence': 'If the unit is operated with the transportation stay attached, abnormal vibration or noise may be generated.'
            }]
        },
        {
            'id': 't03',
            'split': 'test',
            'category': 'refrigerant',
            'type': 'dieu_kien',
            'question': 'In section 14.3.4, why must soap water NEVER be used when testing for refrigerant piping leaks?',
            'expected_answer': 'Soap water may cause cracking of components (such as flare nuts or stop valve caps), may contain salt that absorbs moisture and freezes, and contains ammonia which may lead to corrosion of flared joints.',
            'gold': [{
                'source_id': 'daikin_vrv_ivplus_4p546222_1e_2025_11',
                'page': 21,
                'evidence': 'NEVER use soap water: ▪Soap water may cause cracking of components, such as flare nuts or stop valve caps. ▪Soap water may contain salt, which absorbs moisture that will freeze when the piping gets cold. ▪Soap water contains ammonia which may lead to corrosion of flared joints'
            }]
        },
        {
            'id': 't04',
            'split': 'test',
            'category': 'electrical_control',
            'type': 'truc_tiep',
            'question': 'According to section 15.5, what are the cable specification requirements (cable core and wire size) for indoor-outdoor interconnection wiring?',
            'expected_answer': '2 core cable with a wire size of 0.75 to 1.25 mm².',
            'gold': [{
                'source_id': 'daikin_vrv_ivplus_4p546222_1e_2025_11',
                'page': 30,
                'evidence': '2 core cable 0.75 to1.25 mm²'
            }]
        },
        {
            'id': 't05',
            'split': 'test',
            'category': 'commissioning_troubleshooting',
            'type': 'dieu_kien',
            'question': 'Under Mode 2 field settings in section 16.1.8, under what installation condition must setting [2-49] be changed to 1?',
            'expected_answer': 'When the outdoor unit is installed in the highest position and the height difference between the lowest indoor unit and the outdoor unit exceeds 50 m.',
            'gold': [{
                'source_id': 'daikin_vrv_ivplus_4p546222_1e_2025_11',
                'page': 35,
                'evidence': 'In case the outdoor unit is installed in the highest position (indoor units are installed on a lower position than outdoor units) and the height difference between the lowest indoor unit and the outdoor unit exceeds 50 m, the setting [2‑49] has to be changed to 1.'
            }]
        }
    ]

    all_answerable = dev_questions + test_questions
    assert len(all_answerable) == 20

    # Validate against starter baseline contract
    validate(chunks, [q for q in all_answerable if q['split'] == 'dev'])
    validate(chunks, [q for q in all_answerable if q['split'] == 'test'])
    print("ALL 20 ANSWERABLE QUESTIONS STRICTLY VALIDATED WITH BASELINE.PY CONTRACT!")

    # 3. 4 UNANSWERABLE QUESTIONS (2 DEV, 2 TEST)
    unanswerable = [
        {
            "id": "q_unans_dev_01",
            "split": "dev",
            "category": "refrigerant",
            "question": "What is the procedure and calculation formula for adding R32 refrigerant when retrofitting the VRV IV+ heat recovery system?",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "The Daikin VRV IV+ (REYQ8~20+REMQ5U7Y1B) manual strictly mandates R410A only (page 4 warns against using any other substance) and does not provide any retrofit procedure or calculation formulas for R32 refrigerant."
        },
        {
            "id": "q_unans_dev_02",
            "split": "dev",
            "category": "operation_limits",
            "question": "What is the rated sound pressure level in decibels (dBA) for outdoor unit model REYQ14U7Y1B during standard cooling operation?",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "The manual describes qualitative acoustic symptoms (such as clicking sounds, gas flowing sounds, and tone changes in Section 8), but does not publish quantitative rated sound pressure levels (dBA) or sound power spectrum curves for any unit model."
        },
        {
            "id": "q_unans_test_01",
            "split": "test",
            "category": "refrigerant",
            "question": "What is the approved synthetic refrigeration oil type and viscosity grade (such as Daphne Hermetic Oil FVC68D) required when servicing the VRV IV+ compressor?",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "While the manual mentions oil recovery operation and warns of oil blowing from stop valves, no approved compressor oil type or viscosity grade was identified in this corpus; this makes no claim about other manuals."
        },
        {
            "id": "q_unans_test_02",
            "split": "test",
            "category": "electrical_control",
            "question": "What is the manufacturer part number and maximum switching frequency of the main IGBT power module mounted on the inverter compressor PCB (A1P)?",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "While the manual references PCB A1P for field settings and external pushbuttons (BS1-BS3) in Section 16, no IGBT part number or switching frequency specification was identified in this corpus; this makes no claim about proprietary documents."
        }
    ]

    # Combine into 24 agent cases
    cases = []
    for q in all_answerable:
        case = {
            "id": q["id"],
            "split": q["split"],
            "category": q["category"],
            "question": q["question"],
            "answerable": True,
            "expected_behavior": "search_and_answer"
        }
        if "filter" in q:
            case["filter"] = q["filter"]
        cases.append(case)
    for u in unanswerable:
        cases.append({
            "id": u["id"],
            "split": u["split"],
            "category": u["category"],
            "question": u["question"],
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": u["absence_reason"]
        })

    assert len(cases) == 24
    dev_cases = [c for c in cases if c['split'] == 'dev']
    test_cases = [c for c in cases if c['split'] == 'test']
    assert len(dev_cases) == 17
    assert len(test_cases) == 7

    return all_answerable, cases


def main():
    from benchmark_control import run_builder
    run_builder(build)


if __name__ == '__main__':
    main()
