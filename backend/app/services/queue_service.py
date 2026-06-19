import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.services.forecast_service import get_queue_throughput_for_facility_product

def get_current_date() -> pd.Timestamp:
    return pd.Timestamp.now().normalize()

def add_days_to_date(start_date: pd.Timestamp, days: int) -> str:
    start_date = pd.to_datetime(start_date, errors="coerce")

    if pd.isna(start_date):
        start_date = pd.Timestamp.now().normalize()

    return (start_date + pd.Timedelta(days=int(days or 0))).strftime("%Y-%m-%d")


def compute_schedule_days_from_tree(
    tree: List[Dict[str, Any]]
) -> Tuple[int, Optional[str], Optional[str]]:
    if not tree:
        return 0, None, None

    valid_dates: List[Tuple[pd.Timestamp, pd.Timestamp]] = []

    for row in tree:
        start_date = pd.to_datetime(row.get("start_date"), errors="coerce")
        arrival_date = pd.to_datetime(row.get("arrival_date"), errors="coerce")

        if pd.notna(start_date) and pd.notna(arrival_date):
            valid_dates.append((start_date, arrival_date))

    if not valid_dates:
        return 0, None, None

    min_start_date = min(x[0] for x in valid_dates)
    max_arrival_date = max(x[1] for x in valid_dates)

    total_days = int(
        math.ceil(
            (max_arrival_date - min_start_date).total_seconds() / 86400.0
        )
    )

    return (
        max(total_days, 0),
        min_start_date.strftime("%Y-%m-%d"),
        max_arrival_date.strftime("%Y-%m-%d"),
    )


def build_queue_key(
    supplier_id: str,
    receiver_id: str,
    product: str,
) -> str:
    return f"{str(supplier_id).strip()}|{str(product).upper().strip()}"


def apply_queue_scheduling_to_paths(
    enriched_paths: List[List[Dict[str, Any]]],
    queue_state: Dict[str, Dict[str, float]],
    start_date: pd.Timestamp,
) -> Tuple[List[List[Dict[str, Any]]], int]:
    
    # 1. Setup shell dan cari kedalaman level maksimum (Hulu paling ujung)
    scheduled_paths: List[List[Dict[str, Any]]] = []
    max_level = 0
    
    for path in enriched_paths:
        if not path:
            continue
        scheduled_path = [dict(node) for node in path]
        scheduled_paths.append(scheduled_path)
        max_level = max(max_level, len(scheduled_path) - 1)

    max_completion_day = 0
    
    # GLOBAL REGISTRY: Kapan barang terakhir kali tiba di suatu fasilitas dari hulu?
    # Key: receiver_id, Value: finish_day_raw
    facility_ready_registry: Dict[str, float] = {}

    # 2. Proses serentak dari Level paling dalam (Estate) turun perlahan ke Level 0 (Refinery)
    for current_level in range(max_level, -1, -1):
        for path in scheduled_paths:
            # Jika rute ini lebih pendek dari level yang sedang dicek, lewati
            if current_level >= len(path):
                continue
            
            node = path[current_level]
            
            supplier_id = str(node.get("supplier_id", "")).strip()
            receiver_id = str(node.get("receiver_id", "")).strip()
            product = str(node.get("product", "")).upper().strip()

            queue_key = build_queue_key(supplier_id, receiver_id, product)
            allocated_qty = float(node.get("quantity", 0.0) or 0.0)
            edge_throughput_tpd = float(node.get("throughput_tpd", 0.0) or 0.0)

            throughput_tpd = get_queue_throughput_for_facility_product(
                supplier_id=supplier_id,
                product=product,
                fallback_tpd=edge_throughput_tpd,
            )

            min_edge_days = float(node.get("estimated_days_raw", node.get("estimated_days", 0)) or 0.0)

            # 3. KUNCI KRONOLOGI HULU-HILIR: Barang dari Hulu sudah sampai tanggal berapa?
            upstream_ready_day_raw = facility_ready_registry.get(supplier_id, 0.0)

            cumulative_qty_before = 0.0
            cumulative_qty_after = 0.0

            if throughput_tpd <= 0:
                # Jika throughput tidak ada, hanya andalkan lead time transport
                queue_start_day_raw = upstream_ready_day_raw
                queue_finish_day_raw = upstream_ready_day_raw + min_edge_days
            else:
                state = queue_state.get(queue_key, {})
                cumulative_qty_before = float(state.get("cumulative_qty", 0.0) or 0.0)
                cumulative_qty_after = cumulative_qty_before + allocated_qty

                # KUNCI ANTREAN ANTAR-ORDER: Kapan mesin pabrik ini terakhir kali selesai dari order sebelumnya?
                capacity_start_day_raw = float(state.get("last_finish_day_raw", 0.0) or 0.0)

                # Mesin beroperasi HANYA JIKA: Barang sudah tiba (upstream) DAN Mesin sudah kosong (capacity)
                queue_start_day_raw = max(upstream_ready_day_raw, capacity_start_day_raw)

                processing_days = allocated_qty / throughput_tpd
                actual_edge_days = max(processing_days, min_edge_days)
                queue_finish_day_raw = queue_start_day_raw + actual_edge_days

                # Update memory mesin pabrik ini untuk Order selanjutnya
                queue_state[queue_key] = {
                    "cumulative_qty": cumulative_qty_after,
                    "throughput_tpd": throughput_tpd,
                    "last_finish_day_raw": queue_finish_day_raw,
                }

            # 4. Simpan tanggal estimasi ke dalam output JSON
            queue_start_day = int(math.floor(queue_start_day_raw))
            queue_finish_day = int(math.ceil(queue_finish_day_raw))

            node["queue_key"] = queue_key
            node["queue_cumulative_qty_before"] = round(cumulative_qty_before, 2)
            node["queue_cumulative_qty_after"] = round(cumulative_qty_after, 2)
            node["queue_throughput_tpd"] = round(throughput_tpd, 2)
            node["queue_start_day_raw"] = round(queue_start_day_raw, 4)
            node["queue_finish_day_raw"] = round(queue_finish_day_raw, 4)
            node["queue_start_day"] = queue_start_day
            node["queue_finish_day"] = queue_finish_day
            node["start_date"] = add_days_to_date(start_date, queue_start_day)
            node["arrival_date"] = add_days_to_date(start_date, queue_finish_day)
            node["queue_enabled"] = True

            # 5. CATATAN ESTAFET: Beri tahu fasilitas penerima bahwa barang akan sampai di tanggal ini
            facility_ready_registry[receiver_id] = max(
                facility_ready_registry.get(receiver_id, 0.0),
                queue_finish_day_raw
            )

            max_completion_day = max(max_completion_day, queue_finish_day)

    return scheduled_paths, int(max_completion_day)

def compute_total_estimated_days_by_level(
    enriched_paths: List[List[Dict[str, Any]]]
) -> Tuple[int, List[Dict[str, Any]]]:
    level_to_max_days: Dict[int, int] = {}

    for path in enriched_paths:
        for level, node in enumerate(path):
            level_days = int(node.get("estimated_days", 0) or 0)
            level_to_max_days[level] = max(
                level_to_max_days.get(level, 0),
                level_days,
            )

    breakdown = [
        {
            "level": level,
            "max_estimated_days": int(days),
        }
        for level, days in sorted(level_to_max_days.items())
    ]

    total_days = int(sum(item["max_estimated_days"] for item in breakdown))
    return total_days, breakdown