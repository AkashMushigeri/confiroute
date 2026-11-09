"""CLI script to run all 6 clinical use-case demonstrations."""

import sys
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from confiroute.eval.use_cases import run_all_use_cases


def main():
    print("[USE-CASES] Running all 6 ConfiRoute clinical use-case demonstrations...")
    results = run_all_use_cases(provider="mock")

    for uc_name, data in results.items():
        if isinstance(data, list):
            verified = all(item.get("verified", False) for item in data)
            print(f"  [{'PASS' if verified else 'FAIL'}] {uc_name} (5 sub-scenarios)")
        else:
            verified = data.get("verified", False)
            title = data.get("use_case", uc_name)
            print(f"  [{'PASS' if verified else 'FAIL'}] {title}")

    print("\n[SUCCESS] Use-case artifacts generated:")
    print("  - reports/use_cases/use_case_results.json")
    print("  - reports/use_cases/USE_CASE_DEMONSTRATIONS.md")


if __name__ == "__main__":
    main()
