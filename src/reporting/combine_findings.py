from pathlib import Path
import pandas as pd


def combine_findings(
    inputs: dict[str, Path],
    out_path: Path,
) -> None:
    """
    Combine findings from multiple modules into one canonical file.

    inputs example:
    {
        "leave_leakage": Path("outputs/findings.csv"),
        "lsl_exposure": Path("outputs/lsl_findings.csv"),
    }
    """
    frames = []

    for source_module, path in inputs.items():
        if not path.exists():
            continue

        df = pd.read_csv(path)
        if df.empty:
            continue

        df["source_module"] = source_module
        frames.append(df)

    if frames:
        combined = pd.concat(frames, ignore_index=True)
    else:
        combined = pd.DataFrame()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_path, index=False)
