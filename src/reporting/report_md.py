from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Dict, Optional

report_date = date.today().strftime("%d %b %Y")

# ---------- Paths ----------

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = BASE_DIR / "outputs"
MODULES_DIR = OUTPUTS_DIR / "modules"

LEAVE_FINDINGS_CSV = MODULES_DIR / "leave_leakage_findings.csv"
LEAKAGE_REPORT_CSV = OUTPUTS_DIR / "leakage_report.csv"
REPORT_MD_PATH = OUTPUTS_DIR / "report.md"


# ---------- Data models ----------

@dataclass
class Finding:
    rule_code: str
    severity: str
    employee_id: str
    leave_type: str
    as_of_date: str
    message: str

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> "Finding":
        # Adjust these field names if your CSV uses slightly different headers
        return cls(
            rule_code=row.get("rule_code") or row.get("rule_id") or "",
            severity=row.get("severity", "").upper(),
            employee_id=row.get("employee_id", ""),
            leave_type=row.get("leave_type", ""),
            as_of_date=row.get("as_of_date", ""),
            message=row.get("message") or row.get("description") or "",
        )


@dataclass
class ExposureRow:
    label: str
    amount: float

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> Optional["ExposureRow"]:
        """
        Try a few common column names for exposure amounts.
        If none are present, return None and the exposure section
        will fall back to a 'not available' message.
        """
        label = row.get("label") or row.get("rule_code") or row.get("bucket") or ""
        amount_field_candidates = [
            "estimated_exposure",
            "exposure_amount",
            "leakage_amount",
            "amount",
            "value",
        ]

        amount_value: Optional[float] = None
        for field in amount_field_candidates:
            if field in row and row[field]:
                try:
                    amount_value = float(row[field])
                    break
                except ValueError:
                    continue

        if amount_value is None:
            return None

        return cls(label=label, amount=amount_value)


# ---------- CSV helpers ----------

def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_findings() -> List[Finding]:
    rows = load_csv(LEAVE_FINDINGS_CSV)
    return [Finding.from_row(r) for r in rows]


def load_exposure_rows() -> List[ExposureRow]:
    rows = load_csv(LEAKAGE_REPORT_CSV)
    exposure_rows: List[ExposureRow] = []
    for r in rows:
        er = ExposureRow.from_row(r)
        if er is not None:
            exposure_rows.append(er)
    return exposure_rows


def sort_findings(findings: List[Finding]) -> List[Finding]:
    """Sort findings by severity (HIGH→MEDIUM→LOW), then rule_code, then employee/date."""
    severity_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(
        findings,
        key=lambda f: (
            severity_rank.get(f.severity, 99),
            f.rule_code or "",
            f.employee_id or "",
            f.as_of_date or "",
        ),
    )


# ---------- Review period helpers ----------

def _parse_iso_date(s: str | None) -> Optional[date]:
    """Parse a simple YYYY-MM-DD string into a date, or return None."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _derive_review_period(findings: List[Finding]) -> str:
    """
    Derive a human-readable review period from the findings' as_of_date values.
    Uses the earliest and latest valid dates found.
    """
    dates: List[date] = []
    for f in findings:
        d = _parse_iso_date(f.as_of_date)
        if d is not None:
            dates.append(d)

    if not dates:
        return "Period not specified"

    start = min(dates)
    end = max(dates)

    if start == end:
        return start.strftime("%d %b %Y")

    return f"{start.strftime('%d %b %Y')} to {end.strftime('%d %b %Y')}"


# ---------- Markdown section builders ----------

def build_header(organisation_name: str, review_period: str) -> str:
    return f"""# Leave & Entitlement Leakage Review

**Organisation:** {organisation_name}  
**Review period:** {review_period}  
**Report prepared as at:** {report_date}  

> This report identifies potential leave and entitlement leakage based on the data provided. It highlights potential compliance risks and process issues but does not constitute legal or industrial relations advice.

---
"""


def build_executive_summary(findings: List[Finding]) -> str:
    total_findings = len(findings)
    high = sum(1 for f in findings if f.severity == "HIGH")
    med = sum(1 for f in findings if f.severity == "MEDIUM")
    low = sum(1 for f in findings if f.severity == "LOW")

    distinct_employees = len({f.employee_id for f in findings if f.employee_id})

    paragraph = (
        f"This review analysed leave and entitlement records and identified "
        f"{total_findings} potential issues across approximately "
        f"{distinct_employees} employees. "
        "Findings range from likely compliance breaches to data quality and process issues."
    )

    return f"""## 1. Executive Summary

{paragraph}

**Findings identified**

- High severity: {high}
- Medium severity: {med}
- Low severity: {low}

**Who should read this**

This report is intended for payroll managers and related stakeholders responsible for leave, entitlement and payroll compliance.

---
"""


def build_data_sources_section() -> str:
    return f"""## 2. Data sources

This review was generated from the following analysis outputs within the project `outputs/` directory:

- `{LEAVE_FINDINGS_CSV.relative_to(OUTPUTS_DIR)}`  
- `{LEAKAGE_REPORT_CSV.relative_to(OUTPUTS_DIR)}`  

These outputs were produced by the Leave & Entitlement Leakage engine from payroll and HR CSV extracts supplied by the organisation for the review period.

---
"""


def build_scope_and_methodology() -> str:
    return """## 3. Scope & Methodology

**Data reviewed**

- Leave ledger records
- Leave balances snapshot
- Employee master data
- Other CSV files supplied by the organisation

**Checks performed**

- Rule-based detection of leave and entitlement leakage
- Comparison of ledger movements against balances snapshots
- Identification of negative balances and unexpected accrual patterns
- Consistency checks between employee status and leave activity

**Out of scope**

- Interpretation of awards and enterprise agreements
- Review of employment contracts
- Detailed payroll system configuration

---
"""


def build_key_findings_overview(findings: List[Finding]) -> str:
    high = sum(1 for f in findings if f.severity == "HIGH")
    med = sum(1 for f in findings if f.severity == "MEDIUM")
    low = sum(1 for f in findings if f.severity == "LOW")

    # Build per-rule summary (counts + severity mix)
    rule_summary_lines: List[str] = []
    if findings:
        rule_counts: Dict[str, Dict[str, int]] = {}

        for f in findings:
            code = f.rule_code or "UNSPECIFIED_RULE"
            if code not in rule_counts:
                rule_counts[code] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "TOTAL": 0}

            if f.severity in ("HIGH", "MEDIUM", "LOW"):
                rule_counts[code][f.severity] += 1
            rule_counts[code]["TOTAL"] += 1

        rule_summary_lines.append("")
        rule_summary_lines.append("**Finding types (by rule)**")
        rule_summary_lines.append("")
        rule_summary_lines.append("This table summarises how many findings were raised for each rule and the mix of severities.")
        rule_summary_lines.append("")
        rule_summary_lines.append("| Rule code | Count | Severity mix (H/M/L) |")
        rule_summary_lines.append("|----------|-------|----------------------|")

        for code in sorted(rule_counts.keys()):
            h = rule_counts[code]["HIGH"]
            m = rule_counts[code]["MEDIUM"]
            l = rule_counts[code]["LOW"]
            total = rule_counts[code]["TOTAL"]
            mix = f"{h}H / {m}M / {l}L"
            rule_summary_lines.append(f"| `{code}` | {total} | {mix} |")

    rule_summary = "\n".join(rule_summary_lines)

    return f"""## 4. Key Findings Overview

The automated checks identified the following potential issues:

| Severity | Count | Description |
|---------|-------|-------------|
| <span class="badge-high">High</span>    | {high}   | Likely compliance breach or underpayment risk |
| <span class="badge-medium">Medium</span>  | {med}   | Material risk or policy inconsistency         |
| <span class="badge-low">Low</span>     | {low}   | Data quality or process issue                 |

{rule_summary}

---
"""



def build_detailed_findings(findings: List[Finding]) -> str:
    if not findings:
        return """## 5. Detailed Findings

No findings were identified for the supplied data.

---
"""

    lines: List[str] = ["## 5. Detailed Findings", ""]
    lines.append(
        "Each finding below follows a consistent **Finding → Evidence → Impact → Recommended Action** pattern."
    )
    lines.append("")

    for idx, f in enumerate(findings, start=1):
        lines.append(f"### Finding {idx}: {f.rule_code or 'UNSPECIFIED RULE'}")
        lines.append(f"**Severity:** {f.severity or 'UNSPECIFIED'}")
        lines.append("")
        lines.append("**Finding**")
        lines.append(f"{f.message or 'No description provided.'}")
        lines.append("")
        lines.append("**Evidence**")
        lines.append("")  # ensure bullets render as a proper list

        evidence_bits = []
        if f.employee_id:
            evidence_bits.append(f"Employee ID: `{f.employee_id}`")
        if f.leave_type:
            evidence_bits.append(f"Leave type: `{f.leave_type}`")
        if f.as_of_date:
            evidence_bits.append(f"As at: `{f.as_of_date}`")

        if evidence_bits:
            lines.append("- " + "\n- ".join(evidence_bits))
        else:
            lines.append("- Not specified in the source data.")
        lines.append("")
        lines.append("**Impact / Risk**")
        lines.append(
            "Potential leave or entitlement imbalance. Impact will depend on the underlying award or agreement, "
            "actual pay outcomes and the period over which the issue has occurred."
        )
        lines.append("")
        lines.append("**Recommended Action**")
        lines.append("")  # blank line so the list renders properly

        lines.append(
            "- Validate this finding against source payroll records and employee entitlements.")
        lines.append(
            "- Correct any confirmed configuration or process issues.")
        lines.append(
            "- Consider remediation where underpayments are confirmed.")

        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def build_financial_exposure_section(exposure_rows: List[ExposureRow]) -> str:
    if not exposure_rows:
        return """## 6. Financial Exposure (Indicative)

No exposure estimates were available from the current data extract. If required, leakage estimates can be added to this section in future runs.

---
"""

    total = sum(r.amount for r in exposure_rows)
    lines = [
        "## 6. Financial Exposure (Indicative)",
        "",
        f"- Number of findings with exposure estimates: {len(exposure_rows)}",
        f"- Indicative total exposure (all severities): {total:,.2f}",
        "",
        "> These figures are indicative only and rely on the provided data and simplifying assumptions. "
        "They should be validated before any remediation or accounting decisions are made.",
        "",
        "---",
        "",
    ]

    return "\n".join(lines)


def build_limitations() -> str:
    return """## 7. Limitations & Assumptions

This review is subject to the following limitations:

- Calculations assume the underlying pay rates, loadings and multipliers are correct in the source systems.
- Award and enterprise agreement interpretation is not performed by this tool.
- Holiday calendars, leave rules and accrual settings are assumed to reflect the organisation’s intended configuration.
- Data quality issues (missing records, duplicates, inconsistent identifiers) may affect the completeness and accuracy of the results.

---
"""


def build_next_steps() -> str:
    return """## 8. Recommended Next Steps

1. Prioritise validation of **High** severity findings.
2. Review affected employee records and reconstruct balances where necessary.
3. Correct any identified configuration or process issues in payroll and HR systems.
4. Consider remediation where confirmed underpayments have occurred.
5. Re-run the review after corrections to confirm that leakage has been addressed.

---
"""


def build_appendices() -> str:
    return """## 9. Appendix A – Rule Definitions

This review used a set of automated rules to flag potential leave and entitlement leakage. Examples include:

- Negative balance checks
- Casual employees accruing leave
- Inactive or terminated employees with leave movements
- Unusual accrual or usage patterns

(Expand this list over time to match your `rules.py` definitions.)

---

## 10. Appendix B – Data Fields Used

Key fields used in this analysis include:

- `employee_id`
- `leave_type`
- `as_of_date`
- `balance_units`
- `movement_units`
- `employment_status`

(Additional fields from the supplied CSV files may also be used.)

---

## 11. Appendix C – Full Findings Table

A complete machine-readable version of the findings is available in:

- `outputs/modules/leave_leakage_findings.csv`
- `outputs/leakage_report.csv`
"""


# ---------- Orchestrator ----------

def generate_leave_leakage_report(
    organisation_name: str = "Organisation not specified",
    review_period: str | None = None,
) -> Path:
    """Generate outputs/report.md for the Leave & Entitlement Leakage Review."""
    findings = load_findings()
    sorted_findings = sort_findings(findings)
    exposure_rows = load_exposure_rows()

    if review_period is None:
        review_period = _derive_review_period(sorted_findings)

    parts = [
        build_header(organisation_name, review_period),
        build_executive_summary(sorted_findings),
        build_data_sources_section(),
        build_scope_and_methodology(),
        build_key_findings_overview(sorted_findings),
        build_detailed_findings(sorted_findings),
        build_financial_exposure_section(exposure_rows),
        build_limitations(),
        build_next_steps(),
        build_appendices(),
    ]

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD_PATH.write_text("\n".join(parts), encoding="utf-8")

    return REPORT_MD_PATH


if __name__ == "__main__":
    generate_leave_leakage_report()
    print(f"Generated Markdown report at {REPORT_MD_PATH}")
