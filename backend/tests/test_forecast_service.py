import pytest
from app.services.forecast_service import (
    get_target_days_for_edge,
    apply_estimated_day_rules,
)

def test_get_target_days_for_edge():
    assert get_target_days_for_edge("SomeReceiver") == 15

def test_apply_estimated_day_rules():
    assert apply_estimated_day_rules(1.1, "R1") == 2
    assert apply_estimated_day_rules(0, "R1") == 0
    assert apply_estimated_day_rules(None, "R1") == 0
