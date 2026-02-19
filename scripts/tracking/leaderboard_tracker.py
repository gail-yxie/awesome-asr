"""Fetch and track the Open ASR Leaderboard top models."""

import logging

import pandas as pd
from huggingface_hub import hf_hub_download

from scripts.utils import DATA_DIR, read_json, today_str, write_json

logger = logging.getLogger(__name__)

LEADERBOARD_DATASET = "reach-vb/open-asr-leaderboard-evals-all"
LEADERBOARD_FILE = "original.csv"
LEADERBOARD_JSON = DATA_DIR / "leaderboard.json"

# Column name mapping from CSV to our JSON keys
DATASET_COLUMNS = {
    "AMI WER": "ami",
    "Earnings22 WER": "earnings22",
    "Gigaspeech WER": "gigaspeech",
    "LS Clean WER": "librispeech_clean",
    "LS Other WER": "librispeech_other",
    "SPGISpeech WER": "spgispeech",
    "Tedlium WER": "tedlium",
    "Voxpopuli WER": "voxpopuli",
    "Common Voice WER": "common_voice",
}


def fetch_leaderboard(top_n: int = 10) -> list[dict]:
    """Fetch the Open ASR Leaderboard and return top N models by average WER.

    Returns:
        List of model dicts sorted by avg WER (ascending).
    """
    logger.info("Fetching Open ASR Leaderboard data...")
    try:
        csv_path = hf_hub_download(
            repo_id=LEADERBOARD_DATASET,
            filename=LEADERBOARD_FILE,
            repo_type="dataset",
        )
    except Exception:
        logger.exception("Failed to download leaderboard data")
        return []

    df = pd.read_csv(csv_path)
    df = df.sort_values("Avg. WER").head(top_n).reset_index(drop=True)

    models = []
    for i, row in df.iterrows():
        scores = {}
        for csv_col, key in DATASET_COLUMNS.items():
            val = row.get(csv_col)
            if pd.notna(val):
                scores[key] = round(float(val), 2)

        models.append(
            {
                "rank": i + 1,
                "model_id": row["Model name"],
                "avg_wer": round(float(row["Avg. WER"]), 2),
                "rtfx": round(float(row["RTF"]), 1) if pd.notna(row.get("RTF")) else None,
                "scores": scores,
            }
        )

    logger.info("Fetched top %d models from Open ASR Leaderboard", len(models))
    return models


def check_leaderboard_updates(
    old_models: list[dict], new_models: list[dict]
) -> list[dict]:
    """Compare old and new leaderboard, return newly promoted models.

    A model is "newly promoted" if it appears in new_models but not in old_models.

    Returns:
        List of model dicts that are new to the top N.
    """
    old_ids = {m["model_id"] for m in old_models}
    return [m for m in new_models if m["model_id"] not in old_ids]


def update_leaderboard() -> tuple[list[dict], list[dict]]:
    """Fetch latest leaderboard, compare with stored data, and update if changed.

    Returns:
        Tuple of (current top 10, list of newly promoted models).
    """
    new_top = fetch_leaderboard(top_n=10)
    if not new_top:
        logger.warning("Could not fetch leaderboard; keeping existing data")
        if LEADERBOARD_JSON.exists():
            data = read_json(LEADERBOARD_JSON)
            return data.get("models", []), []
        return [], []

    # Load existing leaderboard
    old_models = []
    if LEADERBOARD_JSON.exists():
        old_data = read_json(LEADERBOARD_JSON)
        old_models = old_data.get("models", [])

    newly_promoted = check_leaderboard_updates(old_models, new_top)

    # Write updated leaderboard
    write_json(
        LEADERBOARD_JSON,
        {"last_updated": today_str(), "models": new_top},
    )
    logger.info("Leaderboard updated. %d new models in top 10.", len(newly_promoted))

    return new_top, newly_promoted


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    models, promoted = update_leaderboard()
    print("Top 10 models:")
    print(json.dumps(models, indent=2))
    if promoted:
        print(f"\nNewly promoted: {[m['model_id'] for m in promoted]}")
