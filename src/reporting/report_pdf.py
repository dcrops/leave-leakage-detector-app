from __future__ import annotations

from pathlib import Path

from markdown import markdown

# We import WeasyPrint lazily so HTML generation still works
# even if WeasyPrint isn't installed or is misconfigured.
try:
    from weasyprint import HTML  # type: ignore[import-untyped]
    WEASYPRINT_AVAILABLE = True
except Exception as e:  # <-- IMPORTANT: WeasyPrint can raise OSError on Windows
    HTML = None  # type: ignore[assignment]
    WEASYPRINT_AVAILABLE = False
    WEASYPRINT_IMPORT_ERROR = str(e)


# ---------- Paths ----------

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = BASE_DIR / "outputs"
REPORT_MD_PATH = OUTPUTS_DIR / "report.md"
REPORT_HTML_PATH = OUTPUTS_DIR / "report.html"
REPORT_PDF_PATH = OUTPUTS_DIR / "report.pdf"


# ---------- HTML template ----------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Leave &amp; Entitlement Leakage Review</title>
  <style>
    /* Base layout */
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      margin: 0;
      padding: 32px;
      background: #f3f4f6;
      color: #1f2933;
      line-height: 1.5;
      font-size: 11pt;
    }}

    .report-container {{
      max-width: 900px;
      margin: 0 auto;
      background: #ffffff;
      padding: 28px 32px;
      border-radius: 10px;
      box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
    }}

    /* Headings */
    h1, h2, h3 {{
      margin-top: 1.6em;
      margin-bottom: 0.6em;
      font-weight: 600;
      color: #111827;
    }}

    h1 {{
      font-size: 20pt;
      margin-top: 0;
      border-bottom: 2px solid #e5e7eb;
      padding-bottom: 8px;
    }}

    h2 {{
      font-size: 14pt;
      border-bottom: 1px solid #e5e7eb;
      padding-bottom: 4px;
    }}

    h3 {{
      font-size: 12pt;
    }}

    p {{
      margin: 0.4em 0 0.9em 0;
    }}

    ul, ol {{
      margin: 0.4em 0 0.9em 1.2em;
    }}

    /* Tables */
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 1em 0 1.4em 0;
      font-size: 10pt;
    }}

    th, td {{
      border: 1px solid #e5e7eb;
      padding: 6px 8px;
      vertical-align: top;
    }}

    th {{
      background: #f9fafb;
      font-weight: 600;
    }}

    /* Inline code / IDs */
    code {{
      font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
      font-size: 90%;
      background: #f3f4f6;
      padding: 1px 3px;
      border-radius: 3px;
    }}

    /* Blockquotes / disclaimer style */
    blockquote {{
      margin: 0.8em 0 1.2em 0;
      padding: 0.6em 1em;
      border-left: 3px solid #d1d5db;
      color: #4b5563;
      background: #f9fafb;
    }}

    hr {{
      border: none;
      border-top: 1px solid #e5e7eb;
      margin: 1.6em 0;
    }}

    /* Print tweaks */
    @media print {{
      body {{
        background: #ffffff;
        padding: 0;
      }}
      .report-container {{
        box-shadow: none;
        border-radius: 0;
        margin: 0;
        max-width: 100%;
      }}
    }}
  </style>
</head>
<body>
  <div class="report-container">
    {content}
  </div>
</body>
</html>
"""


# ---------- Builders ----------

def build_html_from_markdown(
    md_path: Path = REPORT_MD_PATH,
    html_path: Path = REPORT_HTML_PATH,
) -> Path:
    """
    Convert the Markdown report.md into a styled HTML file.
    """
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown report not found: {md_path}")

    md_text = md_path.read_text(encoding="utf-8")

    # Use 'extra' + 'tables' so Markdown tables become proper <table> elements.
    content_html = markdown(md_text, extensions=["extra", "tables"])

    full_html = HTML_TEMPLATE.format(content=content_html)

    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(full_html, encoding="utf-8")

    return html_path


def html_to_pdf(
    html_path: Path = REPORT_HTML_PATH,
    pdf_path: Path = REPORT_PDF_PATH,
) -> Path | None:
    if not html_path.exists():
        raise FileNotFoundError(f"HTML report not found: {html_path}")

    if not WEASYPRINT_AVAILABLE:
        print("WeasyPrint not available; skipping PDF generation.")
        try:
            print(f"Reason: {WEASYPRINT_IMPORT_ERROR}")
        except NameError:
            pass
        return None

    html_text = html_path.read_text(encoding="utf-8")
    HTML(string=html_text).write_pdf(str(pdf_path))
    return pdf_path



def build_html_and_pdf() -> None:
    """
    High-level helper: build report.html from report.md,
    then render report.pdf if possible.
    """
    html_path = build_html_from_markdown()
    print(f"Wrote {html_path}")

    pdf_path = html_to_pdf()
    if pdf_path is not None:
        print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    build_html_and_pdf()
