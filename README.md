# Leave & Entitlement Leakage Detection (AU)

Batch, CSV-based payroll integrity checks for identifying potential leave & entitlement leakage risks in an Australian payroll context.

## Typical use cases

This tool is commonly used for:

- payroll health checks and internal assurance reviews
- pre-audit preparation and risk identification
- validation after payroll system migrations or vendor changes
- investigation of unexplained leave balance discrepancies
- targeted reviews of high-risk employee populations (e.g. casuals)

It is designed to support **review and investigation**, not to automate payroll decisions.

This tool flags *potential* issues for review. It does **not** make legal or payroll decisions.

## What this does

Given three input CSVs:

- `employees.csv` (employee context)
- `leave_ledger.csv` (accrual / taken events)
- `balances_snapshot.csv` (current balances at an as-of date)

The tool produces audit-friendly outputs that help payroll teams identify anomalies and reconcile ledger-derived balances to snapshot balances.

## How to run

```bash 
python -m leave_leakage

## How to interpret the outputs

### 1) `outputs/findings.csv` (audit log)

One row per finding (flag). This is the primary file for payroll review.

**Key columns:**

- `rule_code` — the rule that triggered
- `severity` — HIGH or MEDIUM
- `message` — short human-readable summary
- `diff_units` — numeric difference where applicable (signed)
- `evidence` — structured JSON payload containing:
  - `sources` — input files involved
  - `primary_keys` — identifiers to locate the issue (employee, leave type, dates)
  - `values` — numbers used in the comparison
  - `thresholds` — tolerances applied
  - `explanation` — plain-English proof statement
- `finding_id` — deterministic identifier for the issue, stable across runs and suitable for ticketing and audit traceability
- `next_action` — procedural guidance describing typical payroll investigation steps (non-legal, non-prescriptive)


**Payroll workflow tip:**  
Treat each row as a case note that can be copied into a payroll ticket or sent to a payroll vendor for investigation.

---

### 2) `outputs/summary.csv` (counts by rule and severity)

Summary view showing how many findings were raised per rule and severity.

This file is typically used for triage and prioritisation.

---

### 3) `outputs/summary_by_severity.csv` (severity totals)

High-level view of total findings by severity.

Useful for reporting, escalation decisions, and management visibility.

---

### 4) `outputs/leakage_report.csv` (reconciliation view)

Reconciliation of ledger-derived balances versus snapshot balances by employee and leave type.

Includes:

- `risk_flag` — indicates whether a risk was detected
- `risk_reason` — concise explanation of why the row is flagged

## Severity model

### HIGH
Likely payroll-impacting inconsistency or strong control breach signal.  
Should be reviewed promptly.

### MEDIUM
Suspicious pattern or data-quality anomaly.  
Review when time permits or if repeated.

Severity reflects **review priority only**, not certainty and not legal or compliance risk.

---

## Rules implemented

### `NEGATIVE_BALANCE` (HIGH)
Snapshot balance is below zero.

### `EVENT_SIGN_ANOMALY` (MEDIUM)
TAKEN event with positive units or ACCRUAL event with negative units.

### `TAKEN_BEFORE_START_DATE` (HIGH)
Leave taken before employee start date.

### `CASUAL_ACCRUAL_PRESENT` (HIGH)
Casual employee has accrual events recorded.

### `BALANCE_MISMATCH_LEDGER_VS_SNAPSHOT` (HIGH)
Ledger-derived balance does not match snapshot balance beyond tolerance.

---

## Notes and limitations

- Results depend on the quality and completeness of source extracts.
- Findings indicate potential issues for investigation only.
- This tool does not interpret awards, agreements, contracts, or legal obligations.

## Input schema expectations

This tool assumes clean, well-structured extracts from a payroll system.  
Unexpected formats may result in false positives or missed findings.

### `employees.csv`

Required columns:

- `employee_id` — string, unique per employee
- `employment_type` — one of `CASUAL`, `FULL_TIME`, `PART_TIME`
- `fte` — numeric (0.0–1.0); may be null for CASUAL
- `start_date` — ISO date (`YYYY-MM-DD`)

Assumptions:
- `start_date` represents the first eligible employment date for leave purposes.
- Employment type reflects status at the time of the extract.

---

### `leave_ledger.csv`

Required columns:

- `employee_id` — string
- `leave_type` — string (e.g. `ANNUAL`, `SICK`)
- `event_date` — ISO date (`YYYY-MM-DD`)
- `units` — numeric (hours)
- `event_type` — `ACCRUAL` or `TAKEN`

Assumptions:
- `ACCRUAL` events should have positive units.
- `TAKEN` events should have negative units.
- Ledger represents the full historical sequence up to the snapshot date.

---

### `balances_snapshot.csv`

Required columns:

- `employee_id` — string
- `leave_type` — string
- `as_of_date` — ISO date (`YYYY-MM-DD`)
- `balance_units` — numeric (hours)

Assumptions:
- Snapshot balances are point-in-time values as at `as_of_date`.
- Units are consistent with ledger units (typically hours).

---

## Guardrails and interpretation guidance

To avoid misinterpretation or false positives, reviewers should consider the following:

- Findings indicate **potential issues**, not confirmed payroll errors.
- Timing differences (e.g. late postings, cut-off timing) can legitimately cause mismatches.
- Manual adjustments or migrations may explain anomalies and should be verified before action.
- Casual accrual findings may reflect historical configuration issues rather than current-state errors.
- Balance mismatches within tolerance are intentionally ignored to reduce noise.

This tool is designed to **support investigation**, not replace payroll judgement or industrial interpretation.

## Rule defensibility and review guidance

Each rule is designed to flag potential payroll risk signals that warrant review.  
Rules are intentionally conservative and explainable. Legitimate business or system reasons may exist for a finding.

---

### `NEGATIVE_BALANCE` (HIGH)

**Why this rule exists**  
Negative leave balances are a common indicator of:
- timing or posting errors
- missed accruals
- incorrect entitlement configuration

In many payroll environments, negative balances are restricted or tightly controlled.

**When this may be legitimate**
- approved leave in advance of accrual
- manual adjustments pending approval
- specific enterprise agreements allowing limited negative balances

**Review guidance**
- Confirm approval exists for any advance leave
- Verify accrual posting timing around pay period cut-offs

---

### `EVENT_SIGN_ANOMALY` (MEDIUM)

**Why this rule exists**  
Leave ledgers should follow consistent sign conventions:
- ACCRUAL → positive units
- TAKEN → negative units

Incorrect signs often indicate data import or configuration issues.

**When this may be legitimate**
- non-standard ledger exports
- historical migrations where signs were inverted intentionally

**Review guidance**
- Validate sign conventions used by the source payroll system
- Check whether transformations were applied during data extraction

---

### `TAKEN_BEFORE_START_DATE` (HIGH)

**Why this rule exists**  
Leave taken before an employee’s start date typically indicates:
- incorrect start dates
- employee ID mismatches
- legacy data carried forward incorrectly

**When this may be legitimate**
- rehires with historical leave data
- employee records consolidated from multiple systems

**Review guidance**
- Confirm whether the employee is a rehire
- Validate that start dates align with the payroll system of record

---

### `CASUAL_ACCRUAL_PRESENT` (HIGH)

**Why this rule exists**  
Casual employees in Australia generally do not accrue paid leave.  
Accrual events for casuals are a strong indicator of misclassification or configuration error.

**When this may be legitimate**
- historical accruals prior to employment type change
- data migrations where employment type was updated later
- misclassified employees in the source system

**Review guidance**
- Check employment type history
- Confirm whether accruals ceased after classification change

---

### `BALANCE_MISMATCH_LEDGER_VS_SNAPSHOT` (HIGH)

**Why this rule exists**  
Ledger-derived balances should reconcile to snapshot balances within an acceptable tolerance.  
Mismatches may indicate missing events, incorrect adjustments, or system reconciliation issues.

**When this may be legitimate**
- timing differences between ledger posting and snapshot extraction
- rounding behaviour in payroll systems
- pending manual adjustments

**Review guidance**
- Confirm snapshot timing relative to ledger cut-off
- Check for known rounding or tolerance behaviour in the payroll system
- Review manual adjustments around the as-of date

---

These rules are designed to support **payroll investigation and reconciliation**, not to assert non-compliance or legal conclusions.

## Example usage workflow (practical)

This section illustrates how the tool would typically be used in a payroll or compliance review context.

### 1) Data extraction
Payroll or HR extracts the following from the payroll system for a defined review period:

- employee master data (`employees.csv`)
- leave ledger history up to the review date (`leave_ledger.csv`)
- leave balance snapshot as at the same date (`balances_snapshot.csv`)

Extracts should be taken as close together in time as possible to minimise timing differences.

---

### 2) Run the checks
The tool is executed locally or in a controlled environment:

```bash
python -m leave_leakage

All outputs are written to the `outputs/` directory.

---

### 3) Triage findings

The reviewer starts with:

- `outputs/summary_by_severity.csv` to understand overall risk level
- `outputs/summary.csv` to identify dominant rule types

HIGH severity findings are typically prioritised first.

---

### 4) Investigate individual findings

For each finding in `outputs/findings.csv`:

- Review the `message` and `severity`
- Use the `evidence` JSON to:
  - identify source files
  - locate the employee, leave type, and relevant dates
  - verify the values and tolerances used

Each finding can be treated as a self-contained audit note.

---

### 5) Reconcile balances

Use `outputs/leakage_report.csv` to:

- scan for reconciliation issues across employees and leave types
- identify patterns rather than isolated cases
- support discussions with payroll vendors or internal teams

---

### 6) Outcome

Based on investigation outcomes, actions may include:

- correcting configuration or entitlement rules
- posting manual adjustments
- improving extraction or cut-off processes
- documenting accepted business exceptions

No payroll changes should be made solely on the basis of this tool without appropriate review and approval.

This workflow is designed to support payroll investigation, reconciliation, and assurance activities, not to automate decision-making.

## Engagement and usage model

This tool is intentionally delivered as a **CSV-in / report-out** process.

Typical engagements involve:
- client-provided payroll extracts
- execution of the checks in a controlled environment
- delivery of findings, summaries, and reconciliation views
- optional support interpreting results and remediation patterns

This approach avoids system access, credentials, or live integrations, and is suitable for one-off reviews or periodic health checks.
