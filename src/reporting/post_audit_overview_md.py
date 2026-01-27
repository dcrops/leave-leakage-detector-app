from __future__ import annotations

from datetime import date
from pathlib import Path

report_date = date.today().strftime("%d %b %Y")

# ---------- Paths ----------

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = BASE_DIR / "outputs"

POST_AUDIT_MD_PATH = OUTPUTS_DIR / "post_audit_overview.md"


def generate_post_audit_overview(
    organisation_name: str = "Organisation not specified",
    prepared_as_at: str | None = None,
) -> Path:
    """
    Generate outputs/post_audit_overview.md for the Post-Audit Payroll Compliance Review.
    This is a narrative / framing document that sits alongside the detailed module reports.
    """
    if prepared_as_at is None:
        prepared_as_at = f"{date.today():%d %b %Y}"

    md = f"""# Post-Audit Payroll Compliance Review

**Organisation:** {organisation_name}  
**Prepared as at:** {prepared_as_at}  

> This Post-Audit Review is intended to support internal follow-up after an audit, regulatory review, or external assurance activity. It summarises key risk indicators based on the data provided but does not constitute legal, accounting, or industrial relations advice.

> This review does not re-perform audit procedures or validate audit conclusions.

---

## 1. Purpose of this Review

This Post-Audit Payroll Compliance Review is designed to help the organisation
understand, triage and respond to payroll risk indicators **after** an audit,
regulatory review or external assurance activity.

The review applies the same automated, data-driven checks used in the
Pre-Audit context to:

- provide an indicative view of residual risk
- identify areas where similar issues may arise beyond audited samples
- support internal decision-making on remediation and control improvements

This review does **not** replace audit conclusions, does not re-perform audit
procedures, and does not provide legal or accounting advice. Its purpose is to
support internal follow-up and ongoing risk management.

---

## 2. Relationship to Detailed Reviews

This post-audit review summarises residual risk and remediation themes following audit activity.  
It references findings identified in the following detailed module reviews:

- **Leave & Entitlement Leakage Review**
- **Public Holiday Compliance Review**
- **Long Service Leave (LSL) Exposure Review**

This report does not re-perform audit procedures or validate audit conclusions.  
It is intended to support internal tracking of remediation actions and residual risk assessment.

---

## 3. How to Use This Review

This Post-Audit Review should be read as a **supporting tool** alongside the
audit outcomes, not as a replacement for them.

Recommended approach:

1. Consider this review together with:
   - audit findings and recommendations
   - any internal reports or management responses
2. Use the **Combined Exposure Overview** to understand the distribution of
   residual risk indicators across key payroll areas.
3. Compare risk indicators with audit findings to:
   - identify alignment (where indicators match known issues)
   - surface adjacent or similar risks that may not have been sampled in detail
4. Prioritise follow-up where risk indicators suggest:
   - broader population impact
   - similar issues across multiple locations, cohorts or entitlement types
5. Re-run relevant modules after remediation to confirm reduction in residual risk.

---

## 4. Residual Risk Snapshot

This review draws together residual exposure signals identified across the following modules:

- **Leave & Entitlement Leakage Review**  
  (operational payroll accuracy and entitlement consistency)

- **Long Service Leave (LSL) Exposure Review**  
  (long-horizon entitlement and provision risk)

- **Public Holiday Compliance Review**  
  (state, locality, and calendar-based public holiday alignment)

A consolidated view of findings by severity is provided in the **Combined Exposure Overview**. Post-audit, this should be used to understand where risk indicators remain and where further work may be required.

---

## 5. Alignment with Audit Findings

Where audit findings are available, this review can assist by:

- highlighting areas where automated indicators align with audit issues
- identifying similar patterns in parts of the population that were not sampled
- providing additional context on the potential spread or persistence of issues

Potential use cases include:

- confirming that known issues are isolated or widespread
- identifying additional employees, locations or periods that may warrant review
- supporting communication with stakeholders (Payroll, HR, Finance, Audit and Governance)

The presence of risk indicators does not by itself confirm non-compliance, but it may suggest areas where further analysis, sampling or remediation is appropriate.

---

## 6. Recommended Post-Audit Actions (After Audit Activity)

### A. Alignment with Audit Outcomes

- Map automated risk indicators against audit findings and agreed actions.
- Identify where indicators align with audit conclusions.

### B. Residual Risk Assessment

- Assess whether similar issues may exist beyond audited samples.
- Prioritise review where patterns suggest broader population impact.

### C. Ongoing Monitoring

- Re-run modules after remediation.
- Use periodic re-runs to monitor residual and emerging risk.

---

## 7. Supporting Detailed Reports

This Post-Audit Review is supported by the following detailed reports, which
contain full findings, evidence, and recommended actions:

- **Combined Exposure Overview**  
  `outputs/combined_overview.html`

- **Leave & Entitlement Leakage Review**  
  `outputs/report.html`

- **Long Service Leave (LSL) Exposure Review**  
  `outputs/lsl_report.html`

- **Public Holiday Compliance Review**  
  Provided separately from the stand-alone Public Holiday Compliance tool.

These reports should be retained alongside audit documentation and management responses as part of the organisation's payroll governance records.

---

## 8. Scope, Assumptions & Limitations

This Post-Audit Review is subject to the following limitations:

- The review relies on the accuracy and completeness of the data provided.
- Automated checks are rule-based and may not capture all payroll risks.
- Award, enterprise agreement, and contract interpretation is not performed by this tool.
- This review does not provide legal, accounting, or industrial relations advice.
- Audit scope, sampling and methodology are determined by the relevant audit function and are not replicated here.

The review is intended to support informed post-audit follow-up and prioritisation and should be used alongside professional advice and formal audit outputs.

---

"""

    POST_AUDIT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    POST_AUDIT_MD_PATH.write_text(md, encoding="utf-8")
    return POST_AUDIT_MD_PATH


if __name__ == "__main__":
    path = generate_post_audit_overview()
    print(f"Wrote {path}")
