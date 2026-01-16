from pathlib import Path
from reporting.combine_findings import combine_findings


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

    print("Wrote: outputs/combined_findings.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
