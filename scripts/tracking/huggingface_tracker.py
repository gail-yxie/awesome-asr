"""Fetch recent ASR models and datasets from the HuggingFace Hub."""

import logging
from datetime import datetime, timedelta, timezone

from huggingface_hub import HfApi

from scripts.config import config

logger = logging.getLogger(__name__)


def fetch_models(lookback_hours: int = 48) -> list[dict]:
    """Fetch recently updated ASR models from HuggingFace.

    Args:
        lookback_hours: How far back to search.

    Returns:
        List of model dicts with keys: model_id, author, downloads, likes, url,
        last_modified, pipeline_tag.
    """
    api = HfApi(token=config.hf_token or None)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    models = []
    for model in api.list_models(
        pipeline_tag="automatic-speech-recognition",
        sort="lastModified",
        direction=-1,
        limit=100,
    ):
        if model.last_modified and model.last_modified < cutoff:
            break

        models.append(
            {
                "model_id": model.id,
                "author": model.author or model.id.split("/")[0],
                "downloads": model.downloads or 0,
                "likes": model.likes or 0,
                "url": f"https://huggingface.co/{model.id}",
                "last_modified": (
                    model.last_modified.strftime("%Y-%m-%d")
                    if model.last_modified
                    else None
                ),
                "pipeline_tag": model.pipeline_tag,
            }
        )

    logger.info("Found %d recent ASR models on HuggingFace", len(models))
    return models


def fetch_datasets(lookback_hours: int = 48) -> list[dict]:
    """Fetch recently updated ASR-related datasets from HuggingFace.

    Args:
        lookback_hours: How far back to search.

    Returns:
        List of dataset dicts with keys: dataset_id, author, downloads, url,
        last_modified.
    """
    api = HfApi(token=config.hf_token or None)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    datasets = []
    for ds in api.list_datasets(
        sort="lastModified",
        direction=-1,
        limit=200,
    ):
        if ds.last_modified and ds.last_modified < cutoff:
            break

        # Filter by tags — look for ASR-related datasets
        tags = set(ds.tags or [])
        asr_tags = {
            "automatic-speech-recognition",
            "speech-recognition",
            "audio",
            "speech",
        }
        if not tags & asr_tags:
            continue

        datasets.append(
            {
                "dataset_id": ds.id,
                "author": ds.author or ds.id.split("/")[0],
                "downloads": ds.downloads or 0,
                "url": f"https://huggingface.co/datasets/{ds.id}",
                "last_modified": (
                    ds.last_modified.strftime("%Y-%m-%d")
                    if ds.last_modified
                    else None
                ),
            }
        )

    logger.info("Found %d recent ASR datasets on HuggingFace", len(datasets))
    return datasets


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    m = fetch_models()
    d = fetch_datasets()
    print("=== Models ===")
    print(json.dumps(m[:5], indent=2))
    print("=== Datasets ===")
    print(json.dumps(d[:5], indent=2))
