from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import pandas as pd


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


def rule_negative_balance(snapshot: pd.DataFrame) -> list[Finding]:
    findings: list[Finding] = []

    bad = snapshot[snapshot["balance_units"] < 0].copy()
    for _, row in bad.iterrows():
        findings.append(
            Finding(
                employee_id=str(row["employee_id"]),
                leave_type=str(row["leave_type"]),
                as_of_date=str(row["as_of_date"].date()) if pd.notna(row["as_of_date"]) else None,
                rule_code="NEGATIVE_BALANCE",
                severity="HIGH",
                message=f"Snapshot balance is negative ({row['balance_units']}).",
                evidence="balances_snapshot.balance_units < 0",
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
        findings.append(
            Finding(
                employee_id=str(row["employee_id"]),
                leave_type=str(row["leave_type"]),
                as_of_date=str(row["event_date"].date()) if pd.notna(row["event_date"]) else None,
                rule_code="EVENT_SIGN_ANOMALY",
                severity="MEDIUM",
                message=f"{row['event_type']} event has unexpected sign ({row['units']}).",
                evidence="ledger.event_type vs ledger.units sign mismatch",
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
            findings.append(
                Finding(
                    employee_id=employee_id,
                    leave_type=str(row["leave_type"]),
                    as_of_date=str(event_date.date()),
                    rule_code="TAKEN_BEFORE_START_DATE",
                    severity="HIGH",
                    message=f"Leave TAKEN on {event_date.date()} is before employee start date {start_date.date()}.",
                    evidence="ledger.event_type == TAKEN and ledger.event_date < employees.start_date",
                )
            )

    return findings

def rule_casual_accrual_present(employees: pd.DataFrame, ledger: pd.DataFrame) -> list[Finding]:
    findings: list[Finding] = []

    emp = employees[["employee_id", "employment_type"]].copy()
    emp["employment_type"] = emp["employment_type"].astype(str)

    casual_ids = set(emp[emp["employment_type"] == "CASUAL"]["employee_id"].astype(str))

    if not casual_ids:
        return findings

    accruals = ledger[
        (ledger["employee_id"].astype(str).isin(casual_ids)) &
        (ledger["event_type"] == "ACCRUAL") &
        (ledger["leave_type"].isin(["ANNUAL", "PERSONAL"]))
    ]

    for _, row in accruals.iterrows():
        findings.append(
            Finding(
                employee_id=str(row["employee_id"]),
                leave_type=str(row["leave_type"]),
                as_of_date=str(row["event_date"].date()) if pd.notna(row["event_date"]) else None,
                rule_code="CASUAL_ACCRUAL_PRESENT",
                severity="HIGH",
                message="Casual employee has leave accrual event.",
                evidence="employees.employment_type == CASUAL and ledger.event_type == ACCRUAL",
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
        findings.append(
            Finding(
                employee_id=str(row["employee_id"]),
                leave_type=str(row["leave_type"]),
                as_of_date=str(row["as_of_date"].date())
                if pd.notna(row["as_of_date"])
                else None,
                rule_code="BALANCE_MISMATCH_LEDGER_VS_SNAPSHOT",
                severity="HIGH",
                message=(
                    f"Ledger-derived balance ({row['ledger_balance_units']}) "
                    f"does not match snapshot balance ({row['balance_units']})."
                ),
                diff_units=float(row["diff_units"]),
                evidence="abs(ledger_balance_units - balance_units) > tolerance",
            )
        )

    return findings



