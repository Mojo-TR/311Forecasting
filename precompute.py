import subprocess
import sys
from pathlib import Path

# Precompute scripts as Python modules
PRECOMPUTE_MODULES = [
    "precompute.trends",
    "precompute.metrics",
    "precompute.resolution",
    "precompute.summary",
    "precompute.forecast",
]


def run_module(module_name):
    print(f"\n⚙️  Running {module_name} ...")

    result = subprocess.run(
        [sys.executable, "-m", module_name],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if result.returncode != 0:
        print(f"❌ ERROR: Precompute failed → {module_name}")
        sys.exit(result.returncode)

    print(f"✅ Finished: {module_name}")


def main():
    print("🚀 Starting full precompute pipeline...\n")

    # Ensure precomputed directories exist
    required_dirs = [
        "precomputed_data/trends",
        "precomputed_data/metrics",
        "precomputed_data/resolution",
        "precomputed_data/summary",
        "precomputed_data/forecast",
    ]

    for d in required_dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

    # Run each precompute script
    for module in PRECOMPUTE_MODULES:
        run_module(module)

    print("\n🎉 ALL PRECOMPUTATIONS COMPLETED SUCCESSFULLY!\n")


if __name__ == "__main__":
    main()