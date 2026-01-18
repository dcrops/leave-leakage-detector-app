from datetime import date
from pathlib import Path
from reporting.combine_findings import combine_findings
from reporting.report_md import generate_leave_leakage_report
from reporting.report_pdf import build_html_and_pdf
from reporting.lsl_report_md import generate_lsl_exposure_report
from reporting.combined_overview_md import generate_combined_exposure_overview


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
        review_period = f"Report prepared as at {date.today():%d %b %Y}",
    )

    generate_lsl_exposure_report(
    organisation_name="Example Client Pty Ltd",
    review_period = f"Report prepared as at {date.today():%d %b %Y}",
    )

    generate_combined_exposure_overview(
    organisation_name="Example Client Pty Ltd",
    # leave as None to be dynamic:
    prepared_as_at=None,
    )

        # HTML layer (PDF is best-effort on Windows)
    # Leave & Entitlement Leakage report
    build_html_and_pdf(
        md_path=outputs / "report.md",
        html_path=outputs / "report.html",
        pdf_path=outputs / "report.pdf",  # PDF may be skipped if WeasyPrint isn't available
        page_title="Leave & Entitlement Leakage Review",
    )

    # LSL Exposure report
    build_html_and_pdf(
        md_path=outputs / "lsl_report.md",
        html_path=outputs / "lsl_report.html",
        pdf_path=outputs / "lsl_report.pdf",
        page_title="Long Service Leave (LSL) Exposure Review",
    )

    build_html_and_pdf(
    md_path=outputs / "combined_overview.md",
    html_path=outputs / "combined_overview.html",
    pdf_path=outputs / "combined_overview.pdf",
    page_title="Combined Exposure Overview",
    )

    print("Wrote outputs/combined_findings.csv")
    print("Wrote outputs/report.md / report.html")
    print("Wrote outputs/lsl_report.md / lsl_report.html")
    print("Wrote outputs/combined_overview.md / combined_overview.html")
    # PDFs are best-effort; they may or may not exist depending on WeasyPrint setup.
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
