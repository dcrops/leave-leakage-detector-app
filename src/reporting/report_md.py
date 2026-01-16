from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import pandas as pd


SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _safe_json_loads(s: str | None) -> dict:
    if not s or not isinstance(s, str):
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}


def _fmt_int(n: int) -> str:
    return f"{n:,}"


def _fmt_date_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _sort_severity(s: str) -> int:
    return SEVERITY_ORDER.get(str(s).upper(), 99)


def _top_items(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Get top rule_codes by count, with severity split.
    """
    if df.empty:
        return pd.DataFrame(columns=["rule_code", "severity", "finding_count"])

    out = (
        df.groupby(["rule_code", "severity"], as_index=False)
        .size()
        .rename(columns={"size": "finding_count"})
    )
    out["sev_rank"] = out["severity"].apply(_sort_severity)
    out = out.sort_values(["sev_rank", "finding_count"], ascending=[True, False])
    return out.drop(columns=["sev_rank"]).head(n)


def _pick_example_rows(df: pd.DataFrame, rule_code: str, max_rows: int = 3) -> pd.DataFrame:
    sub = df[df["rule_code"] == rule_code].copy()
    if sub.empty:
        return sub

    sub["sev_rank"] = sub["severity"].apply(_sort_severity)
    sub = sub.sort_values(["sev_rank", "employee_id", "leave_type"], ascending=[True, True, True])
    return sub.head(max_rows).drop(columns=["sev_rank"], errors="ignore")


def _module_name(source_module: str) -> str:
    return {
        "leave_leakage": "Leave Leakage (Ledger vs Snapshot)",
        "lsl_exposure": "Long Service Leave (LSL) Exposure",
    }.get(source_module, source_module)


def build_report_md(findings: pd.DataFrame) -> str:
    now = _fmt_date_now()

    if findings.empty:
        return (
            "# Payroll Compliance Findings Report\n\n"
            f"_Generated: {now}_\n\n"
            "No findings were produced for this run.\n"
        )

    # Normalize
    for col in ["employee_id", "leave_type", "as_of_date", "rule_code", "severity", "message", "source_module"]:
        if col not in findings.columns:
            findings[col] = ""

    findings["severity"] = findings["severity"].astype(str).str.upper()
    findings["source_module"] = findings["source_module"].astype(str)

    # Summary counts
    total = len(findings)
    by_sev = (
        findings.groupby("severity", as_index=False)
        .size()
        .rename(columns={"size": "finding_count"})
    )
    by_sev["sev_rank"] = by_sev["severity"].apply(_sort_severity)
    by_sev = by_sev.sort_values("sev_rank").drop(columns=["sev_rank"])

    by_mod = (
        findings.groupby(["source_module", "severity"], as_index=False)
        .size()
        .rename(columns={"size": "finding_count"})
    )
    by_mod["sev_rank"] = by_mod["severity"].apply(_sort_severity)
    by_mod = by_mod.sort_values(["source_module", "sev_rank"]).drop(columns=["sev_rank"])

    # Top rule codes
    top_rules = _top_items(findings, n=12)

    # Build markdown
    lines: list[str] = []
    lines.append("# Payroll Compliance Findings Report")
    lines.append("")
    lines.append(f"_Generated: {now}_")
    lines.append("")
    lines.append("## Executive summary")
    lines.append("")
    lines.append(f"- Total findings: **{_fmt_int(total)}**")

    sev_map = {row["severity"]: int(row["finding_count"]) for _, row in by_sev.iterrows()}
    lines.append(
        "- Severity breakdown: "
        + ", ".join([f"**{k}** {_fmt_int(v)}" for k, v in sev_map.items()])
    )
    lines.append("")
    lines.append("**What this report is:** A structured set of compliance risk flags with evidence and next actions.")
    lines.append("**What this report is not:** Legal advice or a statutory entitlement calculation.")
    lines.append("")

    # Module overview
    lines.append("## Findings by module")
    lines.append("")
    for mod in by_mod["source_module"].drop_duplicates().tolist():
        mod_rows = by_mod[by_mod["source_module"] == mod]
        parts = []
        for _, r in mod_rows.iterrows():
            parts.append(f"{r['severity']} {_fmt_int(int(r['finding_count']))}")
        lines.append(f"- **{_module_name(mod)}**: " + ", ".join(parts))
    lines.append("")

    # Top drivers
    lines.append("## Top risk drivers (by rule)")
    lines.append("")
    if top_rules.empty:
        lines.append("_No rule-level breakdown available._")
    else:
        for _, r in top_rules.iterrows():
            lines.append(f"- **{r['rule_code']}** ({r['severity']}): {_fmt_int(int(r['finding_count']))} finding(s)")
    lines.append("")

    # Action plan
    lines.append("## Recommended next actions (prioritised)")
    lines.append("")
    lines.append("1. **Address HIGH severity findings first** (data errors, negative balances, eligibility issues).")
    lines.append("2. **Confirm rule intent vs business context** for MEDIUM findings (heuristic flags, policy-specific scenarios).")
    lines.append("3. **Re-run after remediation** to confirm closure and prevent recurrence.")
    lines.append("")

    # Appendix: examples per rule
    lines.append("## Appendix A — Rule examples with evidence (sample)")
    lines.append("")
    unique_rules = (
        findings.assign(sev_rank=findings["severity"].apply(_sort_severity))
        .sort_values(["sev_rank", "rule_code"])
        ["rule_code"]
        .drop_duplicates()
        .tolist()
    )

    for rule in unique_rules:
        sub = _pick_example_rows(findings, rule_code=rule, max_rows=3)
        if sub.empty:
            continue

        # Derive module name from first row
        mod = str(sub.iloc[0].get("source_module", ""))
        sev = str(sub.iloc[0].get("severity", ""))
        lines.append(f"### {rule} ({sev}) — {_module_name(mod)}")
        lines.append("")

        for _, row in sub.iterrows():
            emp = row.get("employee_id", "")
            lt = row.get("leave_type", "")
            dt = row.get("as_of_date", "")
            msg = row.get("message", "")
            nxt = row.get("next_action", "") or ""

            evidence = _safe_json_loads(row.get("evidence"))
            sources = evidence.get("sources") or []
            thresholds = evidence.get("thresholds") or {}
            explanation = evidence.get("explanation") or ""

            lines.append(f"- **Employee:** `{emp}`  | **Leave type:** `{lt}`  | **As of:** `{dt}`")
            lines.append(f"  - **Message:** {msg}")
            if explanation:
                lines.append(f"  - **Evidence:** {explanation}")
            if sources:
                lines.append(f"  - **Sources:** {', '.join([f'`{s}`' for s in sources])}")
            if thresholds:
                # keep it compact
                th_parts = [f"{k}={v}" for k, v in thresholds.items()]
                lines.append(f"  - **Thresholds:** " + ", ".join([f"`{p}`" for p in th_parts]))
            if nxt:
                lines.append(f"  - **Next action:** {nxt}")
            lines.append("")

    lines.append("---")
    lines.append("### Notes")
    lines.append("- Findings are designed to be explainable and auditable (each includes evidence and recommended next actions).")
    lines.append("- LSL exposure estimates (if present) are indicative only and depend on available pay-rate inputs.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    out_dir = repo_root / "outputs"
    combined_path = out_dir / "combined_findings.csv"  # canonical combined file
    report_path = out_dir / "report.md"

    # If the combined findings don't exist, emit a simple placeholder report
    if not combined_path.exists():
        placeholder = (
            "# Payroll Compliance Findings Report\n\n"
            "_Generated: (no combined findings available)_\n\n"
            "No combined findings were found at `outputs/combined_findings.csv`.\n\n"
            "- Run `python -m leave_leakage.run`\n"
            "- Run `python -m lsl_exposure.run`\n"
            "- Run `python -m reporting.run`\n\n"
            "Then re-run `python -m reporting.report_md`.\n"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(placeholder, encoding="utf-8")
        print(f"[report_md] combined_findings.csv not found, wrote placeholder report to {report_path}")
        return 0

    # Try to read the combined findings; treat read failures as 'no findings'
    try:
        df = pd.read_csv(combined_path)
    except Exception as exc:  # pandas EmptyDataError, parser issues, etc.
        print(f"[report_md] Warning: could not read {combined_path}: {exc!r}")
        df = pd.DataFrame()

    md = build_report_md(df)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md, encoding="utf-8")

    print(f"Wrote: {report_path}")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
