from datetime import datetime
from typing import Any, Dict

import pandas as pd

from app.schemas import SLOCConfigRequest
from app.repositories.csv_repository import (
    load_sloc_eudr_config,
    save_sloc_eudr_config,
)
from app.services.stock_service import (
    SLOC_CACHE,
    sloc_cache_lock,
    apply_sloc_config_to_base,
)

def update_sloc_config_service(request: SLOCConfigRequest) -> Dict[str, Any]:
    cfg = load_sloc_eudr_config().copy()

    if cfg.empty:
        cfg = pd.DataFrame(
            columns=[
                "plant",
                "storagelocation",
                "material",
                "eudr",
                "eudr_valid_from",
                "eudr_valid_to",
            ]
        )

    for item in request.items:
        mask = (
            (cfg["plant"].astype(str) == str(item.plant))
            & (cfg["storagelocation"].astype(str) == str(item.storagelocation))
            & (cfg["material"].astype(str) == str(item.material))
        )

        row_data = {
            "plant": str(item.plant),
            "storagelocation": str(item.storagelocation),
            "material": str(item.material),
            "eudr": bool(item.eudr),
            "eudr_valid_from": pd.to_datetime(item.eudr_valid_from, errors="coerce"),
            "eudr_valid_to": pd.to_datetime(item.eudr_valid_to, errors="coerce"),
        }

        if mask.any():
            for key, value in row_data.items():
                cfg.loc[mask, key] = value
        else:
            cfg = pd.concat([cfg, pd.DataFrame([row_data])], ignore_index=True)

    save_sloc_eudr_config(cfg)

    with sloc_cache_lock:
        if SLOC_CACHE["base_sloc_master"] is not None:
            SLOC_CACHE["configured_sloc_master"] = apply_sloc_config_to_base(
                SLOC_CACHE["base_sloc_master"].copy(),
                cfg.copy(),
            )
            SLOC_CACHE["last_refresh_at"] = datetime.utcnow()
        else:
            SLOC_CACHE["configured_sloc_master"] = None
            SLOC_CACHE["last_refresh_at"] = None

    return {
        "status": "ok",
        "updated_items": len(request.items),
    }