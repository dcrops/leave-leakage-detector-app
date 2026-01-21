from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

report_date = date.today().strftime("%d %b %Y")


BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = BASE_DIR / "outputs"
MODULES_DIR = OUTPUTS_DIR / "modules"

OUT_MD = OUTPUTS_DIR / "combined_overview.md"

LEAVE_SUMMARY_BY_SEV = MODULES_DIR / "leave_leakage_summary_by_severity.csv"
LEAVE_FINDINGS = MODULES_DIR / "leave_leakage_findings.csv"

LSL_FINDINGS = MODULES_DIR / "lsl_findings.csv"


@dataclass(frozen=True)
class SevCounts:
    high: int = 0
    medium: int = 0
    low: int = 0

    @property
    def total(self) -> int:
        return self.high + self.medium + self.low


def _load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _normalise_sev(s: str) -> str:
    return (s or "").strip().upper()

def _counts_from_rows(rows: List[Dict[str, str]]) -> SevCounts:
    c = Counter(_normalise_sev(r.get("severity", "")) for r in rows)
    return SevCounts(
        high=c.get("HIGH", 0),
        medium=c.get("MEDIUM", 0),
        low=c.get("LOW", 0),
    )


def _counts_from_findings_csv(path: Path) -> SevCounts:
    rows = _load_csv(path)
    return _counts_from_rows(rows)


def _counts_from_leave_summary_by_sev(path: Path) -> SevCounts:
    """
    Expects a CSV with something like:
    severity,count
    HIGH,12
    MEDIUM,3
    LOW,7

    If columns differ, we fall back to scanning leave findings.
    """
    rows = _load_csv(path)
    if not rows:
        return SevCounts()

    # try a few common column names
    sev_col_candidates = ["severity", "Severity"]
    count_col_candidates = ["count", "Count", "n", "N", "value", "Value"]

    sev_col = next((c for c in sev_col_candidates if c in rows[0]), None)
    count_col = next((c for c in count_col_candidates if c in rows[0]), None)
    if not sev_col or not count_col:
        return SevCounts()

    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for r in rows:
        sev = _normalise_sev(r.get(sev_col, ""))
        try:
            n = int(float(r.get(count_col, "0") or "0"))
        except ValueError:
            n = 0
        if sev in counts:
            counts[sev] += n

    return SevCounts(high=counts["HIGH"], medium=counts["MEDIUM"], low=counts["LOW"])

def _top_rules_from_rows(rows: List[Dict[str, str]], top_n: int = 3) -> List[Tuple[str, int]]:
    if not rows:
        return []
    c = Counter((r.get("rule_code") or r.get("rule_id") or "UNSPECIFIED").strip() for r in rows)
    return c.most_common(top_n)

def _top_rules(path: Path, top_n: int = 3) -> List[Tuple[str, int]]:
    rows = _load_csv(path)
    return _top_rules_from_rows(rows, top_n=top_n)

def _load_deduped_lsl_rows() -> List[Dict[str, str]]:
    """
    Load LSL findings and apply the same deduplication logic used in the LSL report:
    - Remove MEDIUM 'LSL_BALANCE_SUSPICIOUSLY_LOW' findings where the same employee
      already has a HIGH 'LSL_ZERO_BALANCE_FOR_LONG_TENURE' finding.
    """
    rows = _load_csv(LSL_FINDINGS)
    if not rows:
        return []

    # Identify employees with the high-severity zero-balance rule
    employees_with_high_zero = set()
    for r in rows:
        rule = (r.get("rule_code") or r.get("rule_id") or "").strip()
        sev = _normalise_sev(r.get("severity", ""))
        if rule == "LSL_ZERO_BALANCE_FOR_LONG_TENURE" and sev == "HIGH":
            emp = (r.get("employee_id") or "").strip()
            if emp:
                employees_with_high_zero.add(emp)

    deduped: List[Dict[str, str]] = []
    for r in rows:
        rule = (r.get("rule_code") or r.get("rule_id") or "").strip()
        sev = _normalise_sev(r.get("severity", ""))
        emp = (r.get("employee_id") or "").strip()

        if (
            emp in employees_with_high_zero
            and rule == "LSL_BALANCE_SUSPICIOUSLY_LOW"
            and sev == "MEDIUM"
        ):
            # Skip this one – it's effectively covered by the HIGH finding
            continue

        deduped.append(r)

    return deduped

def generate_combined_exposure_overview(
    organisation_name: str = "Organisation not specified",
    prepared_as_at: str | None = None,
) -> Path:
    """
    Creates outputs/combined_overview.md (exec-friendly summary referencing the detailed reports).
    """
    if prepared_as_at is None:
        prepared_as_at = f"{date.today():%d %b %Y}"

    # Leave counts: prefer summary_by_severity if available; else parse findings
    leave_counts = _counts_from_leave_summary_by_sev(LEAVE_SUMMARY_BY_SEV)
    if leave_counts.total == 0:
        leave_counts = _counts_from_findings_csv(LEAVE_FINDINGS)

    # LSL counts: use the same deduplicated logic as the LSL report
    lsl_rows = _load_deduped_lsl_rows()
    lsl_counts = _counts_from_rows(lsl_rows)

    leave_top = _top_rules(LEAVE_FINDINGS, top_n=3)
    lsl_top = _top_rules_from_rows(lsl_rows, top_n=3)

    md = f"""# Combined Exposure Overview

**Organisation:** {organisation_name}  
**Prepared as at:** {prepared_as_at}  
**Report date:** {report_date}  

> This overview summarises key exposure signals identified across payroll compliance modules. It is intended to support prioritisation and internal discussion. It does not constitute legal, accounting, or industrial relations advice.

---

## 1. Executive Summary

This document provides a consolidated, high-level view of exposure identified across:

- **Leave & Entitlement Leakage Review** (operational payroll accuracy and entitlement consistency)
- **Long Service Leave (LSL) Exposure Review** (long-horizon entitlement and provision risk)

Use this overview to support prioritisation of follow-up work. Refer to the detailed module reports for full evidence and recommended actions.

---

## 2. Exposure Snapshot

| Module | High | Medium | Low | Total |
|---|---:|---:|---:|---:|
| Leave & Entitlement Leakage | {leave_counts.high} | {leave_counts.medium} | {leave_counts.low} | {leave_counts.total} |
| Long Service Leave (LSL) Exposure | {lsl_counts.high} | {lsl_counts.medium} | {lsl_counts.low} | {lsl_counts.total} |

**Severity meaning**

- **High** — likely compliance breach / underpayment risk (leave) OR likely exposure / provision risk (LSL)  
- **Medium** — material inconsistency or configuration issue  
- **Low** — data quality or minor process issue  

---

## 3. Key Themes (Top signals)

### Leave & Entitlement Leakage (Top rules)
{_format_top_rules(leave_top)}

### Long Service Leave (LSL) Exposure (Top rules)
{_format_top_rules(lsl_top)}

---

## 4. Recommended Next Steps

1. Prioritise review of **High** severity findings across both modules.
2. For confirmed issues, identify root causes (configuration, process, data, policy).
3. Implement corrections and re-run modules to confirm risk reduction.
4. Where significant exposure is indicated, engage appropriate internal stakeholders (Payroll, HR, Finance) and external advisors if required.

---

## 5. Detailed Reports

Full detail, evidence and recommended actions are available in:

- `outputs/report.html` (Leave & Entitlement Leakage Review)
- `outputs/lsl_report.html` (Long Service Leave Exposure Review)

(If you export PDFs manually from HTML, include them alongside these files.)

---
"""
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")
    return OUT_MD


def _format_top_rules(items: List[Tuple[str, int]]) -> str:
    if not items:
        return "- No findings available."
    return "\n".join([f"- `{rule}` — {count}" for rule, count in items])


if __name__ == "__main__":
    path = generate_combined_exposure_overview()
    print(f"Wrote {path}")
