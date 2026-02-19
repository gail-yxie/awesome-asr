"""Fetch recent ASR models and datasets from the HuggingFace Hub."""

import logging
from datetime import datetime, timedelta, timezone

from huggingface_hub import HfApi

from scripts.config import config

logger = logging.getLogger(__name__)


def fetch_models(lookback_hours: int = 48) -> list[dict]:
    """Fetch newly published ASR models from HuggingFace.

    Only includes models whose ``created_at`` falls within the lookback
    window, so models that were merely *updated* are excluded.

    Args:
        lookback_hours: How far back to search.

    Returns:
        List of model dicts with keys: model_id, author, downloads, likes, url,
        created_at, pipeline_tag.
    """
    api = HfApi(token=config.hf_token or None)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    models = []
    for model in api.list_models(
        pipeline_tag="automatic-speech-recognition",
        sort="createdAt",
        direction=-1,
        limit=200,
    ):
        created = getattr(model, "created_at", None)
        if created and created < cutoff:
            break

        models.append(
            {
                "model_id": model.id,
                "author": model.author or model.id.split("/")[0],
                "downloads": model.downloads or 0,
                "likes": model.likes or 0,
                "url": f"https://huggingface.co/{model.id}",
                "created_at": (
                    created.strftime("%Y-%m-%d") if created else None
                ),
                "pipeline_tag": model.pipeline_tag,
            }
        )

    logger.info("Found %d newly published ASR models on HuggingFace", len(models))
    return models


def fetch_datasets(lookback_hours: int = 48) -> list[dict]:
    """Fetch newly published ASR-related datasets from HuggingFace.

    Only includes datasets whose ``created_at`` falls within the lookback
    window.

    Args:
        lookback_hours: How far back to search.

    Returns:
        List of dataset dicts with keys: dataset_id, author, downloads, url,
        created_at.
    """
    api = HfApi(token=config.hf_token or None)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    datasets = []
    for ds in api.list_datasets(
        sort="createdAt",
        direction=-1,
        limit=200,
    ):
        created = getattr(ds, "created_at", None)
        if created and created < cutoff:
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
                "created_at": (
                    created.strftime("%Y-%m-%d") if created else None
                ),
            }
        )

    logger.info("Found %d newly published ASR datasets on HuggingFace", len(datasets))
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
