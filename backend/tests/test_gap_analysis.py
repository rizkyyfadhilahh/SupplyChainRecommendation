import pytest
from app.services.gap_analysis_service import (
    HistoricalBuyerData,
    DemandProjectionEngine,
    get_gap_analysis_service,
)
from app.services.enterprise_metrics_service import get_enterprise_metrics_calculator
from app.services.pcf_service import get_pcf_service

def test_historical_buyer_data():
    buyers = HistoricalBuyerData.get_all_buyers()
    assert "Neste Oil" in buyers
    
    neste = HistoricalBuyerData.get_buyer_data("Neste Oil")
    assert neste is not None
    assert neste["max_pcf_limit"] == 2.5
    
    profiles = HistoricalBuyerData.get_buyer_profiles()
    assert len(profiles) == len(buyers)
    assert any(p["name"] == "Neste Oil" for p in profiles)

def test_demand_projection_engine():
    historical_orders = [
        {"date": "2024-01-15", "product": "CPO", "quantity": 5000.0},
        {"date": "2024-06-15", "product": "CPO", "quantity": 5000.0},
        {"date": "2025-01-15", "product": "CPO", "quantity": 5000.0},
    ]
    proj = DemandProjectionEngine.project_annual_demand(historical_orders, 2026)
    assert proj["total_quantity"] > 0
    assert proj["projection_year"] == 2026

def test_gap_analysis_service_success():
    service = get_gap_analysis_service()
    res = service.analyze_buyer_gap("Neste Oil", "Lubuk Gaung Refinery")
    
    assert "error" not in res
    assert "projected_demand" in res
    assert "gap_analysis" in res
    assert "shortfall_kg" in res["gap_analysis"]

def test_gap_analysis_service_not_found():
    service = get_gap_analysis_service()
    res = service.analyze_buyer_gap("Unknown Buyer", "Lubuk Gaung Refinery")
    assert "error" in res

def test_generate_fulfillment_routes():
    service = get_gap_analysis_service()
    res = service.analyze_buyer_gap("Neste Oil", "Lubuk Gaung Refinery")
    
    metrics = get_enterprise_metrics_calculator()
    pcf = get_pcf_service()
    
    routes = service.generate_fulfillment_routes(
        gap_analysis=res,
        buyer_name="Neste Oil",
        facility="Lubuk Gaung Refinery",
        metrics_calc=metrics,
        pcf_service=pcf
    )
    
    assert "gap_analysis" in routes
    assert "recommended_routes" in routes
    assert len(routes["recommended_routes"]) == 3
