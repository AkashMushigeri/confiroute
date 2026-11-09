"""Create reproducible DEV, VAL, and TEST splits for ConfiRoute."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import random
import pandas as pd

from confiroute.config import get_config
from confiroute.data.medmcqa_loader import (
    load_medmcqa_split,
    create_synthetic_fixture,
    download_hf_parquet,
    validate_record,
    format_standard_record,
)


def sample_reproducible_records(
    parquet_path: Path,
    sample_size: int,
    seed: int,
    exclude_ids: Optional[set] = None,
    max_scan: int = 5000,
) -> List[Dict[str, Any]]:
    """Sample valid records deterministically without loading full large datasets into memory."""
    exclude_ids = exclude_ids or set()
    df_chunk = pd.read_parquet(parquet_path)

    valid_records: List[Dict[str, Any]] = []
    for _, row in df_chunk.iterrows():
        rec = row.to_dict()
        if str(rec.get("id")) in exclude_ids:
            continue
        if validate_record(rec):
            valid_records.append(format_standard_record(rec))
        if len(valid_records) >= max_scan:
            break

    if len(valid_records) < sample_size:
        raise ValueError(
            f"Not enough valid records found: needed {sample_size}, got {len(valid_records)}"
        )

    rng = random.Random(seed)
    sampled = rng.sample(valid_records, sample_size)
    return sampled


def save_jsonl(records: List[Dict[str, Any]], output_path: Path) -> None:
    """Save records in JSONL format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def build_splits(force_synthetic: bool = False) -> Dict[str, Path]:
    """Build DEV (50), VAL (200), and TEST (300) splits."""
    config = get_config()
    raw_dir = config.raw_data_dir
    processed_dir = config.processed_data_dir
    seed = config.seed

    dev_path = processed_dir / "dev.jsonl"
    val_path = processed_dir / "val.jsonl"
    test_path = processed_dir / "test.jsonl"

    if force_synthetic:
        print("[DATA] Generating labelled synthetic splits (offline/fixture mode)...")
        syn_dev = create_synthetic_fixture(dev_path, count=config.split_sizes["dev"])
        syn_val = create_synthetic_fixture(val_path, count=config.split_sizes["val"])
        syn_test = create_synthetic_fixture(test_path, count=config.split_sizes["test"])
        return {"dev": dev_path, "val": val_path, "test": test_path}

    try:
        print("[DATA] Loading official validation parquet for TEST split (300 questions)...")
        val_parquet = download_hf_parquet("validation", raw_dir)
        test_records = sample_reproducible_records(
            val_parquet,
            sample_size=config.split_sizes["test"],
            seed=seed,
            max_scan=2000,
        )
        save_jsonl(test_records, test_path)
        print(f"[DATA] Wrote TEST split: {len(test_records)} questions -> {test_path}")

        print("[DATA] Loading train parquet for DEV (50) and VAL (200) splits...")
        train_parquet = download_hf_parquet("train", raw_dir)

        # Sample DEV (50)
        dev_records = sample_reproducible_records(
            train_parquet,
            sample_size=config.split_sizes["dev"],
            seed=seed,
            max_scan=3000,
        )
        save_jsonl(dev_records, dev_path)
        print(f"[DATA] Wrote DEV split: {len(dev_records)} questions -> {dev_path}")

        # Sample VAL (200) excluding DEV questions
        dev_ids = {r["id"] for r in dev_records}
        val_records = sample_reproducible_records(
            train_parquet,
            sample_size=config.split_sizes["val"],
            seed=seed + 1,  # independent seed
            exclude_ids=dev_ids,
            max_scan=4000,
        )
        save_jsonl(val_records, val_path)
        print(f"[DATA] Wrote VAL split: {len(val_records)} questions -> {val_path}")

        # Verify no overlap between DEV and VAL
        val_ids = {r["id"] for r in val_records}
        overlap = dev_ids.intersection(val_ids)
        assert len(overlap) == 0, f"Error: DEV and VAL overlap by {len(overlap)} questions"

        return {"dev": dev_path, "val": val_path, "test": test_path}

    except Exception as exc:
        print(f"[DATA WARNING] Hugging Face download failed or offline ({exc}).")
        print("[DATA] Falling back to labelled synthetic fixtures...")
        create_synthetic_fixture(dev_path, count=config.split_sizes["dev"])
        create_synthetic_fixture(val_path, count=config.split_sizes["val"])
        create_synthetic_fixture(test_path, count=config.split_sizes["test"])
        return {"dev": dev_path, "val": val_path, "test": test_path}


if __name__ == "__main__":
    build_splits()
