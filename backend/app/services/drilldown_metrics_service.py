import logging
import random
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.constants.drilldown_catalog import (
    EUDR_ESTATES,
    EUDR_MILLS,
    PRODUCTS,
    MT_TANKERS,
    LOADING_PORTS,
    REFINERY_CURRENT_CAPACITY,
    _ROUTE_KM,
)

logger = logging.getLogger(__name__)

# PCF emission factors
_HARVEST_EMISSION:             float = 0.35
_TRANSPORT_ESTATE_MILL:        float = 0.00012
_MILL_PROCESSING_EMISSION:     float = 0.65
_TRANSPORT_MILL_REFINERY:      float = 0.00015
_REFINERY_PROCESSING_EMISSION: float = 0.85

def calc_pcf_5stage(estate_vol_kg: float, em_km: float, mr_km: float, product: str) -> float:
    return calc_pcf_5stage_breakdown(estate_vol_kg, em_km, mr_km, product)["pcf_per_unit_kg_co2e_per_kg"]

def calc_pcf_5stage_breakdown(
    estate_vol_kg: float, em_km: float, mr_km: float, product: str,
) -> Dict[str, Any]:
    estate_vol_kg = float(estate_vol_kg)
    oer       = float(PRODUCTS.get(product, {}).get("oer", 0.20))
    ref_yield = float(PRODUCTS.get(product, {}).get("ref_yield", 0.94))
    mill_vol  = estate_vol_kg * oer
    ref_vol   = mill_vol * ref_yield
    s1 = round(estate_vol_kg * _HARVEST_EMISSION, 4)
    s2 = round(estate_vol_kg * float(em_km) * _TRANSPORT_ESTATE_MILL, 4)
    s3 = round(mill_vol * _MILL_PROCESSING_EMISSION, 4)
    s4 = round(mill_vol * float(mr_km) * _TRANSPORT_MILL_REFINERY, 4)
    s5 = round(ref_vol  * _REFINERY_PROCESSING_EMISSION, 4)
    total = round(s1 + s2 + s3 + s4 + s5, 4)
    delivered = ref_vol if ref_vol > 0 else estate_vol_kg
    return {
        "stage1_harvest_emission_kg_co2e":             s1,
        "stage2_transport_estate_to_mill_kg_co2e":     s2,
        "stage3_mill_processing_emission_kg_co2e":     s3,
        "stage4_transport_mill_to_refinery_kg_co2e":   s4,
        "stage5_refinery_processing_emission_kg_co2e": s5,
        "total_kg_co2e":                               total,
        "pcf_per_unit_kg_co2e_per_kg":                 round(total / max(delivered, 1.0), 4),
        "estate_volume_kg":    round(estate_vol_kg, 2),
        "mill_volume_kg":      round(mill_vol, 2),
        "refined_volume_kg":   round(ref_vol, 2),
        "estate_to_mill_km":   float(em_km),
        "mill_to_refinery_km": float(mr_km),
    }

def calculate_drilldown_enterprise_metrics(
    estate: Dict[str, str], mill: Dict[str, str], refinery_id: str,
    refinery_group: str, routed_vol_mt: float, product: str,
    buyer_max_pcf: float, historical_volumes: List[float], opt_idx: int,
) -> Dict[str, Any]:
    km = _ROUTE_KM.get(refinery_id, {"em": 80.0, "mr": 380.0})
    em_km = float(km["em"]) * (1.0 - 0.05 * opt_idx)
    mr_km = float(km["mr"]) * (1.0 + 0.03 * opt_idx)
    estate_vol_kg = routed_vol_mt * 1000.0 / max(PRODUCTS.get(product, {}).get("oer", 0.20), 0.001)
    pcf_detail    = calc_pcf_5stage_breakdown(estate_vol_kg, em_km, mr_km, product)
    pcf_pu        = pcf_detail["pcf_per_unit_kg_co2e_per_kg"]
    pcf_total     = round(pcf_pu * routed_vol_mt * 1000.0, 2)

    cap_mt    = float(REFINERY_CURRENT_CAPACITY.get(refinery_group, 35_000.0))
    load_pct  = round(routed_vol_mt / max(cap_mt, 1.0) * 100.0, 2)
    cap_state = "CRITICAL" if load_pct > 95 else "WARNING" if load_pct > 75 else "NORMAL"

    route_dist = em_km + mr_km
    dist_score = round(max(100.0 - (route_dist / 10.0), 10.0), 1)
    dist_level = "HIGH" if dist_score >= 80 else "MEDIUM" if dist_score >= 60 else "LOW"

    avg_hist  = float(sum(historical_volumes) / max(len(historical_volumes), 1))
    dev       = abs(routed_vol_mt - avg_hist) / max(avg_hist, 1.0)
    sim_score = round(max(100.0 - dev * 100.0, 0.0), 1)
    risk      = "LOW" if sim_score >= 75 else "MEDIUM" if sim_score >= 50 else "HIGH"

    buyer_compliance = "WITHIN_LIMIT" if pcf_pu <= float(buyer_max_pcf) else "EXCEEDS_LIMIT"
    overall = round(
        (100.0 - min(pcf_pu / 2.5 * 100.0, 100.0)) * 0.25
        + (100.0 - min(load_pct, 100.0)) * 0.25
        + dist_score * 0.25 + sim_score * 0.25, 1,
    )
    rec = ("OPTIMAL" if cap_state == "NORMAL" and dist_level == "HIGH" and risk == "LOW"
           else "ACCEPTABLE" if cap_state != "CRITICAL" and dist_level != "LOW"
           else "RISKY")

    return {
        "pcf_score": {
            "pcf_total_kg_co2e": pcf_total, "pcf_per_unit_kg_co2e_per_kg": pcf_pu,
            "benchmark_compliance": "COMPLIANT" if pcf_pu <= 2.5 else "AT_RISK",
            "buyer_pcf_limit": float(buyer_max_pcf), "buyer_compliance": buyer_compliance,
            "stage_breakdown": pcf_detail,
        },
        "capacity_constraints": {
            "refinery_group": refinery_group, "available_capacity_mt": cap_mt,
            "requested_volume_mt": round(routed_vol_mt, 2),
            "capacity_load_pct": load_pct, "warning_state": cap_state, "can_fulfill": load_pct <= 100.0,
        },
        "route_distance": {
            "total_distance_km": round(route_dist, 2), "efficiency_score_percent": dist_score,
            "efficiency_level": dist_level,
        },
        "volume_similarity": {
            "similarity_pct": sim_score, "risk_level": risk,
            "routed_volume_mt": round(routed_vol_mt, 2), "historical_avg_mt": round(avg_hist, 2),
            "deviation_pct": round(dev * 100.0, 2),
        },
        "overall_score": overall, "recommendation": rec,
    }

def generate_shipping_history(
    buyer: Dict[str, Any],
    product_code: str,
    product_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    rng = random.Random(hash(buyer["id"] + product_code + "v3"))

    route     = product_data["historical_route"]
    ref_group = route["refinery"]["group"]
    ref_id    = route["refinery"]["id"]
    annual_mt = float(product_data["historical_quantity_mt"])
    km_data   = _ROUTE_KM.get(ref_id, {"em": 80.0, "mr": 380.0})

    n_per_year  = rng.randint(5, 7)
    n_shipments = n_per_year * 2
    today       = date.today()
    base_year   = today.year - 2
    base_vol    = annual_mt / n_per_year

    alt_estates = [e for e in EUDR_ESTATES if e["id"] != route["estate"]["id"]]
    alt_mills   = [m for m in EUDR_MILLS   if m["id"] != route["mill"]["id"]]

    trace_tree: Optional[List[Dict[str, Any]]] = None
    try:
        from app.schemas import TraceRequest, OrderRequest
        from app.services.trace_service import trace_orders_service
        sample_kg = round(base_vol * 1000.0, 2)
        treq = TraceRequest(orders=[OrderRequest(
            facility=ref_group, product=product_code,
            quantity=max(sample_kg, 1000.0), spec="EUDR",
            recommendation_metric="VOLUME",
        )])
        tres = trace_orders_service(treq)
        order_res = tres.get("orders", [{}])[0]
        opts = order_res.get("recommendation_options", [])
        if opts and opts[0].get("tree"):
            trace_tree = opts[0]["tree"]
    except Exception as exc:
        logger.debug("Trace call for shipping history failed: %s", exc)

    shipments: List[Dict[str, Any]] = []
    for i in range(n_shipments):
        month_offset = int(i * (24 / n_shipments)) + rng.randint(0, 1)
        day_offset   = rng.randint(1, 27)
        ship_date    = date(base_year, 1, 1) + timedelta(days=month_offset * 30 + day_offset)
        if ship_date > today:
            ship_date = today - timedelta(days=rng.randint(10, 60))

        vol_mt = round(base_vol * (1.0 + rng.uniform(-0.15, 0.15)), 2)
        year   = ship_date.year

        use_alt = rng.random() < 0.30 and alt_estates and alt_mills
        s_estate  = alt_estates[i % len(alt_estates)] if use_alt else route["estate"]
        s_mill    = alt_mills[i % len(alt_mills)]     if use_alt else route["mill"]
        s_ref     = route["refinery"]

        em_km = float(km_data["em"]) * (1.0 + rng.uniform(-0.08, 0.08))
        mr_km = float(km_data["mr"]) * (1.0 + rng.uniform(-0.08, 0.08))
        estate_vol_kg = vol_mt * 1000.0 / max(PRODUCTS.get(product_code, {}).get("oer", 0.20), 0.001)
        pcf = calc_pcf_5stage_breakdown(estate_vol_kg, em_km, mr_km, product_code)

        if trace_tree and len(trace_tree) >= 2:
            scale = vol_mt * 1000.0 / max(float(trace_tree[0].get("quantity", 1.0)), 1.0)
            supply_chain = []
            for node in trace_tree[:6]:
                n = dict(node)
                n["quantity"] = round(float(n.get("quantity", 0)) * scale, 2)
                supply_chain.append(n)
            source = "trace_engine"
        else:
            ffb_kg  = estate_vol_kg
            cpo_kg  = round(ffb_kg * 0.20, 2)
            prod_kg = round(cpo_kg * PRODUCTS.get(product_code, {}).get("ref_yield", 0.94), 2)
            supply_chain = [
                {"level": 0, "supplier_id": s_estate["id"],  "supplier_name": s_estate["name"],
                 "supplier_type": "ESTATE",   "product": "FFB",          "quantity": round(ffb_kg, 2),
                 "receiver_id": s_mill["id"],    "estimated_days": rng.randint(2, 4)},
                {"level": 0, "supplier_id": alt_estates[(i+1) % len(alt_estates)]["id"],
                 "supplier_name": alt_estates[(i+1) % len(alt_estates)]["name"],
                 "supplier_type": "ESTATE",   "product": "FFB",
                 "quantity": round(ffb_kg * 0.35, 2),
                 "receiver_id": s_mill["id"],    "estimated_days": rng.randint(2, 5)},
                {"level": 1, "supplier_id": s_mill["id"],    "supplier_name": s_mill["name"],
                 "supplier_type": "MILL",     "product": "CPO",          "quantity": round(cpo_kg * 1.35, 2),
                 "receiver_id": s_ref["id"],     "estimated_days": rng.randint(4, 8)},
                {"level": 2, "supplier_id": s_ref["id"],     "supplier_name": s_ref["name"],
                 "supplier_type": "REFINERY", "product": product_code,  "quantity": round(prod_kg * 1.35, 2),
                 "receiver_id": "BUYER_DEST", "estimated_days": rng.randint(1, 3)},
            ]
            source = "dummy"

        has_eudr  = s_estate.get("spec", "") == "EUDR"
        has_rspo  = rng.random() < 0.78
        has_iscc  = rng.random() < 0.62
        has_mspo  = rng.random() < 0.50
        has_ispo  = rng.random() < 0.42
        certs = {
            "eudr":  has_eudr,
            "rspo":  has_rspo,
            "iscc":  has_iscc,
            "mspo":  has_mspo,
            "ispo":  has_ispo,
            "eudr_dds_reference":      f"EUDR-DDS-{rng.randint(1000000, 9999999)}" if has_eudr  else None,
            "rspo_certificate_number": f"RSPO-{rng.randint(100000, 999999)}"        if has_rspo  else None,
            "iscc_certificate_number": f"ISCC-EU-{rng.randint(10000, 99999)}"       if has_iscc  else None,
            "mspo_certificate_number": f"MSPO-{rng.randint(10000, 99999)}"          if has_mspo  else None,
            "ispo_certificate_number": f"ISPO-{rng.randint(10000, 99999)}"          if has_ispo  else None,
            "audit_date":       (ship_date - timedelta(days=rng.randint(30, 180))).isoformat(),
            "next_audit_due":   (ship_date + timedelta(days=rng.randint(180, 365))).isoformat(),
        }
        cert_count = sum([has_eudr, has_rspo, has_iscc, has_mspo, has_ispo])

        vessel   = MT_TANKERS[rng.randint(0, len(MT_TANKERS) - 1)]
        loading  = LOADING_PORTS.get(ref_group, "Jakarta, Indonesia")
        discharge = buyer.get("discharge_port", "Rotterdam, Netherlands")

        shipments.append({
            "shipment_id":            f"SHP-{buyer['id'][-4:]}-{product_code}-{year}-{i+1:02d}",
            "date":                   ship_date.isoformat(),
            "year":                   year,
            "volume_mt":              vol_mt,
            "status":                 "DELIVERED",
            "product":                product_code,
            "product_label":          PRODUCTS.get(product_code, {}).get("label", product_code),
            "vessel_name":            vessel,
            "bl_number":              f"BL-{year}-{rng.randint(10000, 99999)}",
            "loading_port":           loading,
            "discharge_port":         discharge,
            "grade":                  f"{product_code} Bulk",
            "moisture_ffa_pct":       round(rng.uniform(0.05, 0.22), 3),
            "estimated_days":         rng.randint(10, 21),
            "route": {
                "estate":   {"id": s_estate["id"],  "name": s_estate["name"],  "spec": s_estate.get("spec","EUDR"), "type": "ESTATE"},
                "mill":     {"id": s_mill["id"],    "name": s_mill["name"],    "spec": s_mill.get("spec","EUDR"),   "type": "MILL"},
                "refinery": {"id": s_ref["id"],     "name": s_ref["name"],     "group": s_ref.get("group",""),     "type": "REFINERY"},
            },
            "supply_chain": supply_chain,
            "supply_chain_source":    source,
            "pcf_breakdown":          pcf,
            "certificates":           certs,
            "cert_count":             cert_count,
            "recommended_as_template": (
                ship_date.year >= today.year - 1
                and pcf["pcf_per_unit_kg_co2e_per_kg"] <= float(buyer["max_pcf_limit"])
                and has_eudr
            ),
        })

    shipments.sort(key=lambda s: s["date"])
    return shipments
