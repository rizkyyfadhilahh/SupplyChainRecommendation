import logging
import random
from typing import Any, Dict, List, Optional
from cachetools import cached, TTLCache

from app.config import CACHE_TTL_SECONDS
from app.constants.drilldown_catalog import (
    BUYER_CATALOGUE,
    _BUYER_INDEX,
    EUDR_ESTATES,
    EUDR_MILLS,
    REFINERIES,
    PRODUCTS,
    REFINERY_CURRENT_CAPACITY,
)
from app.services.drilldown_metrics_service import (
    calc_pcf_5stage_breakdown,
    generate_shipping_history,
    calculate_drilldown_enterprise_metrics,
)

logger = logging.getLogger(__name__)

# ── Public service functions ───────────────────────────────────────────────

@cached(cache=TTLCache(maxsize=1024, ttl=CACHE_TTL_SECONDS))
def get_buyers_list() -> List[Dict[str, Any]]:
    return [
        {"id": b["id"], "name": b["name"], "country": b["country"],
         "segment": b["segment"], "max_pcf_limit": float(b["max_pcf_limit"]),
         "products": list(b["products"].keys())}
        for b in BUYER_CATALOGUE
    ]

@cached(cache=TTLCache(maxsize=1024, ttl=CACHE_TTL_SECONDS))
def get_capacity_heatmap() -> Dict[str, Any]:
    heatmap = []
    for ref_name, cap_mt in REFINERY_CURRENT_CAPACITY.items():
        rng = random.Random(hash(ref_name + "heatmap"))
        total_annual = cap_mt / (1.0 - rng.uniform(0.12, 0.40))
        committed = total_annual - cap_mt
        util_pct  = round(committed / total_annual * 100.0, 1)
        heatmap.append({
            "refinery":          ref_name,
            "total_capacity_mt": round(total_annual, 0),
            "committed_mt":      round(committed, 0),
            "available_mt":      round(cap_mt, 0),
            "utilization_pct":   util_pct,
            "status": "CRITICAL" if util_pct > 88 else "WARNING" if util_pct > 72 else "NORMAL",
        })
    return {"refineries": heatmap}

def get_product_context(buyer_id: str, product_code: str) -> Dict[str, Any]:
    buyer = _BUYER_INDEX.get(buyer_id)
    if not buyer:
        raise ValueError(f"Buyer '{buyer_id}' not found.")
    product_data = buyer["products"].get(product_code)
    if not product_data:
        raise ValueError(f"Buyer '{buyer['name']}' has no history for product '{product_code}'.")

    route         = product_data["historical_route"]
    refinery_group = route["refinery"]["group"]
    refinery_id    = route["refinery"]["id"]

    historical_qty_mt   = float(product_data["historical_quantity_mt"])
    projected_demand_mt = round(historical_qty_mt * 1.05, 2)
    current_capacity_mt = float(REFINERY_CURRENT_CAPACITY.get(refinery_group, 35_000.0))

    unmet_demand_mt  = max(projected_demand_mt - current_capacity_mt, 0.0)
    fulfillment_pct  = min(round(current_capacity_mt / projected_demand_mt * 100.0, 2), 100.0) \
                       if projected_demand_mt > 0 else 0.0
    unmet_pct        = round(max(100.0 - fulfillment_pct, 0.0), 2)

    if unmet_demand_mt <= 0.0:   gap_status = "FULFILLED"
    elif unmet_pct > 30.0:       gap_status = "CRITICAL"
    elif unmet_pct > 10.0:       gap_status = "MODERATE"
    else:                         gap_status = "MINOR"

    # Assume average distances for context PCF calc if not specified
    km_data       = {"em": 80.0, "mr": 380.0} 
    estate_vol_kg = historical_qty_mt * 1000.0 / max(PRODUCTS.get(product_code, {}).get("oer", 0.20), 0.001)
    pcf_breakdown = calc_pcf_5stage_breakdown(estate_vol_kg, km_data["em"], km_data["mr"], product_code)

    shipping_history = generate_shipping_history(buyer, product_code, product_data)

    return {
        "buyer_id":      buyer_id,
        "buyer_name":    buyer["name"],
        "country":       buyer["country"],
        "segment":       buyer["segment"],
        "max_pcf_limit": float(buyer["max_pcf_limit"]),
        "discharge_port": buyer.get("discharge_port", "—"),
        "product_code":  product_code,
        "product_label": product_data["label"],
        "historical": {
            "quantity_mt": historical_qty_mt,
            "route": {
                "estate":   {**route["estate"],   "type": "ESTATE"},
                "mill":     {**route["mill"],     "type": "MILL"},
                "refinery": {**route["refinery"], "type": "REFINERY"},
            },
            "pcf_per_unit_kg_co2e_per_kg": float(product_data.get("historical_pcf_per_unit",
                                                  pcf_breakdown["pcf_per_unit_kg_co2e_per_kg"])),
            "pcf_5stage_computed": pcf_breakdown["pcf_per_unit_kg_co2e_per_kg"],
            "pcf_breakdown": pcf_breakdown,
        },
        "shipping_history": shipping_history,
        "forecast": {
            "projected_demand_mt":  projected_demand_mt,
            "current_capacity_mt":  current_capacity_mt,
            "fulfillment_pct":      fulfillment_pct,
            "unmet_demand_mt":      round(unmet_demand_mt, 2),
            "unmet_demand_pct":     unmet_pct,
            "gap_status":           gap_status,
            "has_gap":              unmet_demand_mt > 0.0,
        },
    }

def get_resolution_routes(
    buyer_id: str, product_code: str, context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if context is None:
        context = get_product_context(buyer_id, product_code)
    buyer    = _BUYER_INDEX[buyer_id]
    unmet_mt = float(context["forecast"]["unmet_demand_mt"])
    if unmet_mt <= 0.0:
        return {"has_gap": False, "routes": []}

    buyer_max_pcf = float(buyer["max_pcf_limit"])
    hist_vols     = [float(p["historical_quantity_mt"]) for p in buyer["products"].values()]
    hist_route    = context["historical"]["route"]
    hist_ref_id   = hist_route["refinery"]["id"]
    alt_estates   = [e for e in EUDR_ESTATES if e["id"] != hist_route["estate"]["id"]]
    alt_mills     = [m for m in EUDR_MILLS   if m["id"] != hist_route["mill"]["id"]]
    ref_opts = ([r for r in REFINERIES if r["id"] == hist_ref_id]
                + [r for r in REFINERIES if r["id"] != hist_ref_id])

    ARCHETYPES = [
        {"label": "Volume-Optimized",      "focus": "VOLUME",       "share": 0.50},
        {"label": "Low Carbon (PCF-First)", "focus": "PCF",          "share": 0.30},
        {"label": "Distance-First",     "focus": "DISTANCE", "share": 0.20},
    ]
    routes = []
    for i, arch in enumerate(ARCHETYPES):
        vol_mt     = max(round(unmet_mt * arch["share"], 2), unmet_mt / 3)
        estate     = alt_estates[i % len(alt_estates)]
        mill       = alt_mills[i % len(alt_mills)]
        refinery   = ref_opts[i % len(ref_opts)]
        oer        = float(PRODUCTS.get(product_code, {}).get("oer", 0.20))
        ref_yield  = float(PRODUCTS.get(product_code, {}).get("ref_yield", 0.94))
        ffb_mt     = vol_mt / max(oer, 0.001)
        cpo_mt     = ffb_mt * oer
        refined_mt = cpo_mt * ref_yield
        em = calculate_drilldown_enterprise_metrics(estate, mill, refinery["id"], refinery["group"],
                                  refined_mt, product_code, buyer_max_pcf, hist_vols, i)
        routes.append({
            "route_id": f"ALT-ROUTE-{i+1}", "route_label": arch["label"],
            "optimization_focus": arch["focus"],
            "fulfillment_share_pct": arch["share"] * 100.0,
            "estimated_days": 8 + i * 2,
            "supply_chain_path": [
                {"level": 0, "supplier_type": "ESTATE",   "supplier_id": estate["id"],
                 "supplier_name": estate["name"],          "supplier_spec": estate.get("spec","EUDR"),
                 "product": "FFB", "quantity_mt": round(ffb_mt, 2),
                 "receiver_id": mill["id"],                "estimated_days": 3},
                {"level": 1, "supplier_type": "MILL",     "supplier_id": mill["id"],
                 "supplier_name": mill["name"],            "supplier_spec": mill.get("spec","EUDR"),
                 "product": "CPO" if product_code in ("CPO","RBDPO","RBDOLN") else "PKO",
                 "quantity_mt": round(cpo_mt, 2),
                 "receiver_id": refinery["id"],            "estimated_days": 5 + i},
                {"level": 2, "supplier_type": "REFINERY", "supplier_id": refinery["id"],
                 "supplier_name": refinery["name"],        "supplier_spec": "EUDR",
                 "product": product_code, "quantity_mt": round(refined_mt, 2),
                 "receiver_id": f"BUYER_{buyer['name'].upper().replace(' ','_')}",
                 "estimated_days": 2},
            ],
            "routed_volume_mt": round(refined_mt, 2),
            "enterprise_metrics": em,
        })

    total_routed = round(sum(r["routed_volume_mt"] for r in routes), 2)
    combined_pct = round(min(total_routed / max(unmet_mt, 1.0) * 100.0, 100.0), 2)
    return {
        "has_gap": True, "unmet_demand_mt": unmet_mt,
        "routes": routes, "total_routed_mt": total_routed,
        "combined_coverage_pct": combined_pct,
    }

async def get_resolution_routes_from_trace(
    buyer_id: str, product_code: str, context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if context is None:
        context = get_product_context(buyer_id, product_code)
    buyer    = _BUYER_INDEX.get(buyer_id)
    unmet_mt = float(context["forecast"]["unmet_demand_mt"])
    if not buyer or unmet_mt <= 0.0:
        return {"has_gap": False, "recommendation_options": [], "source": "none"}

    refinery_group = context["historical"]["route"]["refinery"]["group"]

    try:
        from app.schemas import TraceRequest, OrderRequest
        from app.services.trace_service import trace_orders_service

        orders_payload = [OrderRequest(
            facility=refinery_group, product=product_code,
            quantity=unmet_mt * 1000.0, spec="EUDR", buyer=None,
            recommendation_metric="VOLUME",
        )]
        trace_result  = trace_orders_service(TraceRequest(orders=orders_payload))
        order_results = trace_result.get("orders", [])

        if order_results and order_results[0].get("recommendation_options"):
            order_result = order_results[0]
            order_result["source"] = "trace_engine"
            order_result["has_gap"] = True
            return order_result

        raise ValueError("No real trace tree generated")

    except Exception as exc:
        logger.warning("Trace-based resolution failed (%s), using fallback.", exc)
        result = get_resolution_routes(buyer_id, product_code, context)
        tree = []
        for r in result.get("routes", []):
            path = r.get("supply_chain_path", [])
            for n in path:
                tree.append({
                    "supplier_id": n.get("supplier_id"),
                    "supplier_type": n.get("supplier_type"),
                    "supplier_name": n.get("supplier_name"),
                    "product": n.get("product"),
                    "quantity": float(n.get("quantity_mt", 0)) * 1000.0,
                    "receiver_id": n.get("receiver_id", refinery_group),
                    "estimated_days": n.get("estimated_days"),
                    "level": n.get("level")
                })
        return {
            "has_gap": True,
            "facility": refinery_group,
            "product": product_code,
            "quantity": unmet_mt * 1000.0,
            "source": "dummy_fallback",
            "recommendation_options": [{
                "option_type": "Dummy Fallback Route",
                "tree": tree
            }]
        }
