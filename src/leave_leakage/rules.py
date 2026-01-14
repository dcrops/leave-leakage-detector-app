from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import json
import hashlib


@dataclass
class Finding:
    employee_id: str
    leave_type: Optional[str]
    as_of_date: Optional[str]
    rule_code: str
    severity: str  # LOW / MEDIUM / HIGH
    message: str
    diff_units: Optional[float] = None
    evidence: Optional[str] = None
    finding_id: Optional[str] = None
    next_action: Optional[str] = None


def compute_finding_id(rule_code: str, evidence_json: Optional[str]) -> str:
    """
    Deterministic ID based on rule_code + evidence.primary_keys.
    Stable across runs provided primary_keys remain stable.
    """
    primary_keys = {}
    if evidence_json:
        try:
            payload = json.loads(evidence_json)
            primary_keys = payload.get("primary_keys") or {}
        except Exception:
            primary_keys = {}

    parts = [rule_code]
    for k in sorted(primary_keys.keys()):
        parts.append(f"{k}={primary_keys.get(k)}")

    canonical = "|".join(parts)
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]



def rule_negative_balance(snapshot: pd.DataFrame) -> list[Finding]:
    findings: list[Finding] = []

    bad = snapshot[snapshot["balance_units"] < 0].copy()
    for _, row in bad.iterrows():
        evidence_str = json.dumps(
        {
            "sources": ["balances_snapshot.csv"],
            "primary_keys": {
                "employee_id": str(row["employee_id"]),
                "leave_type": str(row["leave_type"]),
                "as_of_date": str(row["as_of_date"].date()) if pd.notna(row["as_of_date"]) else None,
            },
            "values": {
                "snapshot_balance_units": float(row["balance_units"]) if pd.notna(row["balance_units"]) else None,
            },
            "thresholds": {
                "expected": "balance_units >= 0"
            },
            "explanation": (
                f"Snapshot balance is negative ({float(row['balance_units'])})."
            ),
        },
        ensure_ascii=False,
        )
        findings.append(
            Finding(
                employee_id=str(row["employee_id"]),
                leave_type=str(row["leave_type"]),
                as_of_date=str(row["as_of_date"].date()) if pd.notna(row["as_of_date"]) else None,
                rule_code="NEGATIVE_BALANCE",
                severity="HIGH",
                message=f"Snapshot balance is negative ({row['balance_units']}).",
                evidence=evidence_str,
                finding_id=compute_finding_id("NEGATIVE_BALANCE", evidence_str),
                next_action=(
                    "Review the employee’s leave ledger and recent payroll adjustments "
                    "to confirm whether the negative balance reflects a data error, "
                    "timing difference, or an approved leave arrangement."
                ),
            )
        )

    return findings

def rule_event_sign_anomaly(ledger: pd.DataFrame) -> list[Finding]:
    findings: list[Finding] = []

    bad = ledger[
        ((ledger["event_type"] == "ACCRUAL") & (ledger["units"] < 0)) |
        ((ledger["event_type"] == "TAKEN") & (ledger["units"] > 0))
    ].copy()

    for _, row in bad.iterrows():
        evidence_str = json.dumps(
        {
            "sources": ["leave_ledger.csv"],
            "primary_keys": {
                "employee_id": str(row["employee_id"]),
                "leave_type": str(row["leave_type"]),
                "event_date": str(row["event_date"].date()) if pd.notna(row["event_date"]) else None,
            },
            "values": {
                "event_type": str(row["event_type"]),
                "units": float(row["units"]) if pd.notna(row["units"]) else None,
                "observed_sign": (
                    "positive" if float(row["units"]) > 0 else "negative"
                ),
                "expected_sign": "negative" if str(row["event_type"]).upper() == "TAKEN" else "positive",
            },
            "thresholds": {
                "expected": "TAKEN units < 0, ACCRUAL units > 0"
            },
            "explanation": (
                f"{str(row['event_type']).upper()} event has unexpected sign."
            ),
        },
        ensure_ascii=False,
    )

    findings.append(
        Finding(
            employee_id=str(row["employee_id"]),
            leave_type=str(row["leave_type"]),
            as_of_date=str(row["event_date"].date()) if pd.notna(row["event_date"]) else None,
            rule_code="EVENT_SIGN_ANOMALY",
            severity="MEDIUM",
            message=f"{row['event_type']} event has unexpected sign ({row['units']}).",
            evidence=evidence_str,
            finding_id=compute_finding_id("EVENT_SIGN_ANOMALY", evidence_str),
            next_action=(
                    "Review the leave ledger configuration and data ingestion rules to confirm expected sign conventions for TAKEN and ACCRUAL events. "
                    "Check whether this entry reflects a system configuration issue, import mapping error, or manual adjustment."
                ),
        )
    )

    return findings

def rule_taken_before_start_date(employees: pd.DataFrame, ledger: pd.DataFrame) -> list[Finding]:
    findings: list[Finding] = []

    # Create a lookup: employee_id -> start_date
    emp = employees[["employee_id", "start_date"]].copy()
    emp["start_date"] = pd.to_datetime(emp["start_date"], errors="raise")
    start_map = dict(zip(emp["employee_id"].astype(str), emp["start_date"]))

    taken = ledger[ledger["event_type"] == "TAKEN"].copy()

    for _, row in taken.iterrows():
        employee_id = str(row["employee_id"])
        start_date = start_map.get(employee_id)

        # If we don't know the start date, we can't evaluate this rule
        if start_date is None:
            continue

        event_date = row["event_date"]
        if pd.isna(event_date):
            continue

        if event_date < start_date:
            evidence_str = json.dumps(
                {
                    "sources": ["employees.csv", "leave_ledger.csv"],
                    "primary_keys": {
                        "employee_id": str(employee_id),
                        "leave_type": str(row["leave_type"]),
                        "event_date": str(event_date.date()) if pd.notna(event_date) else None,
                    },
                    "values": {
                        "event_type": str(row["event_type"]),
                        "units": float(row["units"]) if pd.notna(row["units"]) else None,
                        "employee_start_date": str(start_date.date()) if pd.notna(start_date) else None,
                    },
                    "thresholds": {
                        "rule": "event_date < start_date (TAKEN only)"
                    },
                    "explanation": (
                        f"Leave TAKEN on {str(event_date.date())} occurs before employee start date "
                        f"{str(start_date.date())}."
                    ),
                },
                ensure_ascii=False,
            )

            findings.append(
                Finding(
                    employee_id=employee_id,
                    leave_type=str(row["leave_type"]),
                    as_of_date=str(event_date.date()),
                    rule_code="TAKEN_BEFORE_START_DATE",
                    severity="HIGH",
                    message=f"Leave TAKEN on {event_date.date()} is before employee start date {start_date.date()}.",
                    evidence=evidence_str,
                    finding_id=compute_finding_id("TAKEN_BEFORE_START_DATE", evidence_str),
                    next_action=(
                    "Verify the employee start date in HR/payroll and the leave event date in the ledger. "
                    "If either is incorrect due to migration/backdating, correct the source record and re-run; "
                    "if intentional (e.g., back-pay correction), document the reason and approval."
                ),
                )
            )

    return findings

def rule_casual_accrual_present(employees: pd.DataFrame, ledger: pd.DataFrame) -> list[Finding]:
    findings: list[Finding] = []

    merged = ledger.merge(
        employees[["employee_id", "employment_type"]],
        on="employee_id",
        how="left",
    )

    merged["employment_type"] = merged["employment_type"].astype(str)

    accruals = merged[
        (merged["employment_type"] == "CASUAL")
        & (merged["event_type"] == "ACCRUAL")
        & (merged["leave_type"].isin(["ANNUAL", "PERSONAL"]))
    ]


    for _, row in accruals.iterrows():
        evidence_str = json.dumps(
            {
                "sources": ["employees.csv", "leave_ledger.csv"],
                "primary_keys": {
                    "employee_id": str(row["employee_id"]),
                    "leave_type": str(row["leave_type"]),
                    "event_date": str(row["event_date"].date()) if pd.notna(row["event_date"]) else None,
                },
                "values": {
                    "employment_type": str(row["employment_type"]),
                    "event_type": str(row["event_type"]),
                    "units": float(row["units"]) if pd.notna(row["units"]) else None,
                },
                "thresholds": {
                    "expected": "CASUAL employees should not have leave ACCRUAL events"
                },
                "explanation": (
                    f"Employee is CASUAL but has an ACCRUAL event "
                    f"on {str(row['event_date'].date())} for {float(row['units'])} units."
                ),
            },
            ensure_ascii=False,
        )

        findings.append(
            Finding(
                employee_id=str(row["employee_id"]),
                leave_type=str(row["leave_type"]),
                as_of_date=str(row["event_date"].date()) if pd.notna(row["event_date"]) else None,
                rule_code="CASUAL_ACCRUAL_PRESENT",
                severity="HIGH",
                message="Casual employee has leave accrual event.",
                evidence=evidence_str,
                finding_id=compute_finding_id("CASUAL_ACCRUAL_PRESENT", evidence_str),
                next_action=(
                    "Confirm the employee’s employment type in HR/payroll and review leave accrual configuration. "
                    "If the employee is incorrectly classified as CASUAL, correct the classification; "
                    "if the accrual is unintended, disable or reverse the accrual and document the remediation."
                ),
            )
        )

    return findings

def rule_balance_mismatch(
    snapshot: pd.DataFrame,
    ledger_recon: pd.DataFrame,
    tolerance: float = 0.01,
) -> list[Finding]:

    findings: list[Finding] = []

    mismatches = ledger_recon[
        (ledger_recon["diff_units"].abs() > tolerance)
    ].copy()

    for _, row in mismatches.iterrows():
        evidence_str = json.dumps(
            {
                "sources": ["leave_ledger.csv", "balances_snapshot.csv"],
                "primary_keys": {
                    "employee_id": str(row["employee_id"]),
                    "leave_type": str(row["leave_type"]),
                    "as_of_date": str(row["as_of_date"].date()) if pd.notna(row["as_of_date"]) else None,
                },
                "values": {
                    "ledger_derived_balance": float(row["ledger_balance_units"]),
                    "snapshot_balance": float(row["balance_units"]),
                    "difference": float(row["diff_units"]),
                },
                "thresholds": {
                    "tolerance_hours": float(tolerance),
                },
                "explanation": (
                    f"Ledger-derived balance differs from snapshot by "
                    f"{abs(float(row['diff_units'])):.2f} hours, "
                    f"exceeding tolerance {float(tolerance):.2f} hours."
                ),
            },
            ensure_ascii=False,
        )

        findings.append(
            Finding(
                employee_id=str(row["employee_id"]),
                leave_type=str(row["leave_type"]),
                as_of_date=str(row["as_of_date"].date()) if pd.notna(row["as_of_date"]) else None,
                rule_code="BALANCE_MISMATCH_LEDGER_VS_SNAPSHOT",
                severity="HIGH",
                message=(
                    f"Ledger-derived balance ({row['ledger_balance_units']}) "
                    f"does not match snapshot balance ({row['balance_units']})."
                ),
                diff_units=float(row["diff_units"]),
                evidence=evidence_str,
                finding_id=compute_finding_id("BALANCE_MISMATCH_LEDGER_VS_SNAPSHOT", evidence_str),
                next_action=(
                    "Reconcile the ledger period and snapshot 'as_of_date' for this leave type. "
                    "Check for missing/duplicate ledger events, timing cut-offs, or manual adjustments, "
                    "then confirm which source is authoritative for reporting."
                ),
            )
        )

    return findings



