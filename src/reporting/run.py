from pathlib import Path
from reporting.combine_findings import combine_findings
from reporting.report_md import generate_leave_leakage_report
from reporting.report_pdf import build_html_and_pdf


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    outputs = repo_root / "outputs"

    combine_findings(
        inputs={
            "leave_leakage": outputs / "modules" / "leave_leakage_findings.csv",
            "lsl_exposure": outputs / "modules" / "lsl_findings.csv",
        },
        out_path=outputs / "combined_findings.csv",
    )

    # generate Markdown report
    generate_leave_leakage_report(
        organisation_name="Example Client Pty Ltd",
        review_period="1 Jan 2024 – 31 Dec 2024",
    )

    # HTML + PDF layer
    build_html_and_pdf()

    print("Wrote outputs/combined_findings.csv")
    print("Wrote outputs/report.md / report.html / report.pdf")

    print("Wrote outputs/combined_findings.csv")
    print("Wrote outputs/report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
