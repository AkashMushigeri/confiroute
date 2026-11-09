"""MedMCQA loader, validation, and conversion utilities."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
import json
import pandas as pd


def index_to_letter(cop: Any) -> str:
    """Convert raw correct option indicator to 'A', 'B', 'C', or 'D'.

    MedMCQA typically uses 0, 1, 2, 3 (or 1, 2, 3, 4, or strings '0'-'3' or 'A'-'D').
    """
    if cop is None:
        raise ValueError("Correct option index cannot be None")

    if isinstance(cop, str):
        cleaned = cop.strip().upper()
        if cleaned in {"A", "B", "C", "D"}:
            return cleaned
        try:
            val = int(cleaned)
        except ValueError:
            raise ValueError(f"Unrecognized option string: {cop}")
    elif isinstance(cop, (int, float)):
        val = int(cop)
    else:
        raise ValueError(f"Unsupported cop type {type(cop)}: {cop}")

    # 0-indexed (0=A, 1=B, 2=C, 3=D)
    mapping_0 = {0: "A", 1: "B", 2: "C", 3: "D"}
    # 1-indexed (1=A, 2=B, 3=C, 4=D)
    mapping_1 = {1: "A", 2: "B", 3: "C", 4: "D"}

    if val in mapping_0:
        return mapping_0[val]
    elif val in mapping_1:
        return mapping_1[val]
    else:
        raise ValueError(f"Option index {val} out of valid range [0, 4]")


def validate_record(record: Dict[str, Any]) -> bool:
    """Validate that a record has all 4 valid options, non-empty question, and valid cop."""
    required_fields = ["id", "question", "opa", "opb", "opc", "opd"]
    for field in required_fields:
        val = record.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False

    # Check choice_type if present
    choice_type = record.get("choice_type")
    if choice_type and str(choice_type).strip().lower() not in {"single", "none", ""}:
        return False

    # Validate correct option can be converted
    cop = record.get("cop")
    if cop is None:
        return False
    try:
        index_to_letter(cop)
    except ValueError:
        return False

    return True


def format_standard_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Transform raw MedMCQA dict into the standard ConfiRoute schema."""
    cop_letter = index_to_letter(raw["cop"])
    raw_subject = raw.get("subject_name")
    raw_topic = raw.get("topic_name")

    # Handle float NaN or None
    subject_str = (
        "General Medicine"
        if raw_subject is None or pd.isna(raw_subject) or not str(raw_subject).strip()
        else str(raw_subject).strip()
    )
    topic_str = (
        "General"
        if raw_topic is None or pd.isna(raw_topic) or not str(raw_topic).strip()
        else str(raw_topic).strip()
    )

    return {
        "id": str(raw["id"]),
        "question": str(raw["question"]).strip(),
        "options": {
            "A": str(raw["opa"]).strip(),
            "B": str(raw["opb"]).strip(),
            "C": str(raw["opc"]).strip(),
            "D": str(raw["opd"]).strip(),
        },
        "correct_letter": cop_letter,
        "subject": subject_str,
        "topic": topic_str,
    }


def download_hf_parquet(split_name: str, dest_dir: Path) -> Path:
    """Download MedMCQA parquet file from Hugging Face if not already present."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{split_name}-00000-of-00001.parquet"
    local_path = dest_dir / filename
    if local_path.exists() and local_path.stat().st_size > 0:
        return local_path

    url = f"https://huggingface.co/datasets/openlifescienceai/medmcqa/resolve/main/data/{filename}"
    req = urllib.request.Request(url, headers={"User-Agent": "ConfiRoute/0.1.0 (Mozilla/5.0)"})
    print(f"Downloading {url} to {local_path}...")
    with urllib.request.urlopen(req, timeout=60) as resp, open(local_path, "wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    print(f"Downloaded {filename} ({local_path.stat().st_size} bytes)")
    return local_path


def load_medmcqa_split(split_name: str, raw_dir: Path, max_rows: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load and validate records from local parquet file, downloading if needed."""
    parquet_path = download_hf_parquet(split_name, raw_dir)
    df = pd.read_parquet(parquet_path)
    records: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        rec = row.to_dict()
        if validate_record(rec):
            records.append(format_standard_record(rec))
            if max_rows and len(records) >= max_rows:
                break

    return records


def create_synthetic_fixture(output_path: Path, count: int = 20) -> List[Dict[str, Any]]:
    """Generate clearly labelled synthetic fixtures for offline testing."""
    samples = [
        {
            "id": "syn-001",
            "question": "Which of the following is the standard first-line treatment for uncomplicated community-acquired pneumonia in an otherwise healthy adult?",
            "options": {"A": "Amoxicillin", "B": "Ciprofloxacin", "C": "Gentamicin", "D": "Vancomycin"},
            "correct_letter": "A",
            "subject": "Pharmacology",
            "topic": "Antibiotics",
        },
        {
            "id": "syn-002",
            "question": "A 55-year-old male presents with acute crushing chest pain, ST-elevation in leads II, III, and aVF. What is the immediate priority intervention?",
            "options": {"A": "Administer IV insulin", "B": "Emergency coronary reperfusion / cardiac cath", "C": "Oral amoxicillin", "D": "Lumbar puncture"},
            "correct_letter": "B",
            "subject": "Cardiology",
            "topic": "Myocardial Infarction",
        },
        {
            "id": "syn-003",
            "question": "What is the recommended pediatric acetaminophen dosage?",
            "options": {"A": "10-15 mg/kg every 4-6 hours", "B": "50 mg/kg every 2 hours", "C": "100 mg/kg single dose", "D": "0.1 mg/kg once daily"},
            "correct_letter": "A",
            "subject": "Pediatrics",
            "topic": "Medication Dosage",
        },
        {
            "id": "syn-004",
            "question": "Which vitamin deficiency leads to Wernicke encephalopathy?",
            "options": {"A": "Vitamin B1 (Thiamine)", "B": "Vitamin C", "C": "Vitamin D", "D": "Vitamin K"},
            "correct_letter": "A",
            "subject": "Neurology",
            "topic": "Nutritional Deficiencies",
        },
        {
            "id": "syn-005",
            "question": "What is the specific antidote for acute acetaminophen toxicity / overdose?",
            "options": {"A": "N-acetylcysteine", "B": "Naloxone", "C": "Flumazenil", "D": "Atropine"},
            "correct_letter": "A",
            "subject": "Toxicology",
            "topic": "Poisoning Antidotes",
        },
    ]

    # Replicate or cycle to reach requested count if needed
    result: List[Dict[str, Any]] = []
    for i in range(count):
        base = samples[i % len(samples)].copy()
        base["id"] = f"syn-{i+1:03d}"
        result.append(base)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in result:
            f.write(json.dumps(r) + "\n")

    return result
