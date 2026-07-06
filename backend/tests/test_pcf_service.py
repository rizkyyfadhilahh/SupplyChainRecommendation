import pytest
from app.services.pcf_service import DummyPCFDataSource, PCFCalculationService

def test_dummy_pcf_data_source():
    source = DummyPCFDataSource()
    # Test facility PCF
    assert source.get_pcf_by_facility("Lubuk Gaung Refinery") == 2.45
    assert source.get_pcf_by_facility("Unknown Refinery") == 2.50
    
    # Test supplier PCF
    assert source.get_pcf_by_supplier("Unknown Supplier", "CPO") == 2.50
    
    # Test 5 stage calculation
    res = source.calculate_5stage_pcf(
        estate_volume_kg=1000.0,
        estate_to_mill_km=100.0,
        mill_processing_kg=200.0,
        mill_to_refinery_km=500.0,
        refinery_processing_kg=188.0
    )
    assert "total_pcf_kg_co2e" in res
    assert res["stage1_harvest_emission_kg_co2e"] > 0
    assert res["stage5_refinery_processing_emission_kg_co2e"] > 0

def test_pcf_calculation_service():
    service = PCFCalculationService()
    
    node = {"supplier_type": "ESTATE", "supplier_id": "EST_1", "product": "FFB", "quantity": 1000.0}
    pcf = service.calculate_node_pcf(node)
    assert pcf > 0
    
    node_mill = {"supplier_type": "MILL", "supplier_id": "MILL_1", "product": "CPO", "quantity": 200.0}
    pcf_mill = service.calculate_node_pcf(node_mill)
    assert pcf_mill > 0
    
    node_zero = {"supplier_type": "ESTATE", "supplier_id": "EST_2", "product": "FFB", "quantity": 0.0}
    assert service.calculate_node_pcf(node_zero) == 0.0

def test_calculate_tree_total_pcf():
    service = PCFCalculationService()
    tree = [
        {"supplier_type": "ESTATE", "quantity": 1000.0},
        {"supplier_type": "MILL", "quantity": 200.0},
        {"supplier_type": "REFINERY", "quantity": 188.0}
    ]
    total = service.calculate_tree_total_pcf(tree, "Facility")
    assert total > 0

def test_calculate_per_unit_pcf():
    service = PCFCalculationService()
    tree = [
        {"supplier_type": "ESTATE", "quantity": 1000.0},
    ]
    per_unit = service.calculate_per_unit_pcf(tree, 188.0, "Facility")
    assert per_unit > 0

    assert service.calculate_per_unit_pcf(tree, 0.0, "Facility") == 0.0
