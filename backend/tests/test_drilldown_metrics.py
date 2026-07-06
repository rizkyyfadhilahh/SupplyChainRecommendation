import pytest
from app.services.drilldown_metrics_service import (
    calc_pcf_5stage,
    calc_pcf_5stage_breakdown,
    calculate_drilldown_enterprise_metrics,
    generate_shipping_history,
)

def test_calc_pcf_5stage_breakdown():
    res = calc_pcf_5stage_breakdown(
        estate_vol_kg=1000.0,
        em_km=80.0,
        mr_km=350.0,
        product="CPO"
    )
    assert "total_kg_co2e" in res
    assert res["pcf_per_unit_kg_co2e_per_kg"] > 0
    assert res["estate_volume_kg"] == 1000.0

def test_calc_pcf_5stage():
    val = calc_pcf_5stage(1000.0, 80.0, 350.0, "CPO")
    assert isinstance(val, float)
    assert val > 0

def test_calculate_drilldown_enterprise_metrics():
    estate = {"id": "E1", "name": "Estate", "spec": "EUDR"}
    mill = {"id": "M1", "name": "Mill", "spec": "EUDR"}
    res = calculate_drilldown_enterprise_metrics(
        estate=estate,
        mill=mill,
        refinery_id="R113",
        refinery_group="Lubuk Gaung Refinery",
        routed_vol_mt=5000.0,
        product="CPO",
        buyer_max_pcf=2.5,
        historical_volumes=[4000.0, 5000.0, 6000.0],
        opt_idx=0
    )
    assert "pcf_score" in res
    assert "capacity_constraints" in res
    assert "route_distance" in res
    assert "volume_similarity" in res
    assert res["capacity_constraints"]["can_fulfill"] is True

def test_generate_shipping_history():
    buyer = {
        "id": "B1",
        "name": "Buyer 1",
        "max_pcf_limit": 2.5,
        "discharge_port": "Port",
    }
    product_data = {
        "historical_quantity_mt": 10000.0,
        "historical_route": {
            "estate": {"id": "E1", "name": "E1", "spec": "EUDR"},
            "mill": {"id": "M1", "name": "M1", "spec": "EUDR"},
            "refinery": {"id": "R113", "name": "Refinery", "group": "Lubuk Gaung Refinery"}
        }
    }
    history = generate_shipping_history(buyer, "CPO", product_data)
    assert len(history) > 0
    assert "shipment_id" in history[0]
    assert "volume_mt" in history[0]
    assert history[0]["status"] == "DELIVERED"
