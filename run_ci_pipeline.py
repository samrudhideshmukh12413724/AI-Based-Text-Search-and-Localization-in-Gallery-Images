"""Local CI/CD Pipeline Runner for AI Image Search Project.

Executes all pipeline stages:
1. Backend Pytest Unit, Integration, & OCR Suite
2. Real-World E2E Query Regression & Grounded Bounding Box Validation
3. Mobile App Flutter Static Analysis & Test Suite
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Configure UTF-8 for Windows PowerShell / Terminal
sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
MOBILE_DIR = ROOT_DIR / "mobile_app"

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_stage(title: str):
    print(f"\n{BOLD}{CYAN}{'=' * 65}{RESET}")
    print(f"{BOLD}{CYAN}  STAGE: {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 65}{RESET}\n")


def run_stage(name: str, cmd: list[str], cwd: Path, use_shell: bool = False) -> tuple[bool, float, str]:
    print_stage(name)
    start = time.time()
    try:
        proc = subprocess.run(
            cmd if not use_shell else " ".join(cmd),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=use_shell,
            encoding="utf-8",
            errors="replace",
        )
        duration = round(time.time() - start, 2)
        output = proc.stdout
        print(output)
        if proc.returncode == 0:
            print(f"{GREEN}✓ {name} PASSED ({duration}s){RESET}")
            return True, duration, output
        else:
            print(f"{RED}✗ {name} FAILED (Exit Code: {proc.returncode}, {duration}s){RESET}")
            return False, duration, output
    except Exception as e:
        duration = round(time.time() - start, 2)
        print(f"{RED}✗ {name} ERROR: {e}{RESET}")
        return False, duration, str(e)


def main():
    print(f"\n{BOLD}{YELLOW}================================================================={RESET}")
    print(f"{BOLD}{YELLOW}      AI IMAGE SEARCH - FULL AUTOMATED CI/CD PIPELINE           {RESET}")
    print(f"{BOLD}{YELLOW}================================================================={RESET}")

    total_start = time.time()
    stage_results = []

    # 1. Pytest Backend Unit & Integration Tests (excluding E2E regression)
    success_unit, dur_unit, _ = run_stage(
        name="Backend Core Tests (OCR Engine, Exact Search, Deduplication, APIs)",
        cmd=[sys.executable, "-m", "pytest", "tests/test_ocr_engine.py", "tests/test_exact_search.py", "tests/test_duplicate_collapsing.py", "tests/test_highlighting.py", "tests/test_api_endpoints.py", "-v", "--tb=short"],
        cwd=BACKEND_DIR,
    )
    stage_results.append(("Backend Core Test Suite", success_unit, dur_unit))

    # 2. Pytest End-to-End Search Regression Suite (all 10 real queries)
    success_e2e, dur_e2e, _ = run_stage(
        name="E2E Query Regression & Bounding Box Gate (10 Target Queries)",
        cmd=[sys.executable, "-m", "pytest", "tests/test_e2e_regression.py", "-v", "--tb=short"],
        cwd=BACKEND_DIR,
    )
    stage_results.append(("E2E Query Regression Gate", success_e2e, dur_e2e))

    # 3. Flutter Mobile App Tests
    flutter_found = subprocess.run("where flutter", shell=True, capture_output=True).returncode == 0
    if flutter_found and MOBILE_DIR.exists():
        success_flt, dur_flt, _ = run_stage(
            name="Mobile App Flutter Tests (Widget & Unit Tests)",
            cmd=["flutter", "test"],
            cwd=MOBILE_DIR,
            use_shell=True,
        )
        stage_results.append(("Flutter Mobile App Tests", success_flt, dur_flt))
    else:
        print(f"{YELLOW}Skipping Flutter tests (Flutter CLI not in PATH){RESET}")

    # Summary
    total_time = round(time.time() - total_start, 2)
    all_passed = all(r[1] for r in stage_results)

    print(f"\n{BOLD}================================================================={RESET}")
    print(f"{BOLD}                     CI/CD PIPELINE SUMMARY                      {RESET}")
    print(f"{BOLD}================================================================={RESET}")
    for name, ok, dur in stage_results:
        status_str = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  [{status_str}] {name:<52} ({dur}s)")
    print(f"-----------------------------------------------------------------")
    print(f"  Total Duration: {total_time}s")
    
    if all_passed:
        print(f"\n{BOLD}{GREEN}✓ ALL CI/CD PIPELINE STAGES PASSED! Ready for Production.{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{BOLD}{RED}✗ CI/CD PIPELINE FAILED. Please review the failed stages above.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
