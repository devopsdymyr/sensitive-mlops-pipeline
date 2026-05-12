"""Stage 1: materialize raw Iris data for DVC-tracked storage."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.datasets import load_iris


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "raw" / "iris.csv",
    )
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    bunch = load_iris(as_frame=True)
    df = bunch.frame.rename(
        columns={
            "sepal length (cm)": "sepal_length",
            "sepal width (cm)": "sepal_width",
            "petal length (cm)": "petal_length",
            "petal width (cm)": "petal_width",
            "target": "target",
        }
    )
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out}")


if __name__ == "__main__":
    main()
