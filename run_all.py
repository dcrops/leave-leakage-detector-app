from subprocess import run
import sys

# Use the same interpreter that is running this script
PYTHON = sys.executable

COMMANDS = [
    [PYTHON, "-m", "leave_leakage.run"],
    [PYTHON, "-m", "lsl_exposure.run"],
    [PYTHON, "-m", "reporting.run"],
    [PYTHON, "-m", "reporting.report_md"],
]


def main() -> None:
    print(f"Using Python interpreter: {PYTHON}")
    for cmd in COMMANDS:
        print(f"\n▶ Running: {' '.join(cmd)}")
        result = run(cmd)
        if result.returncode != 0:
            print("❌ Command failed, stopping pipeline.")
            sys.exit(result.returncode)

    print("\n✅ All compliance checks and reports completed successfully.")


if __name__ == "__main__":
    main()
