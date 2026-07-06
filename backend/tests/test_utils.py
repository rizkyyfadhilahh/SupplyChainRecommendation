import pytest
import pandas as pd
from app.utils import (
    normalize_columns, normalize_facility_type,
    normalize_spec_value, normalize_trace_product,
    safe_mean, safe_median, round_days_up, is_valid_value
)

def test_normalize_columns():
    df = pd.DataFrame({"  Col 1 ": [1], "COL_2": [2]})
    df = normalize_columns(df)
    assert list(df.columns) == ["col_1", "col_2"]

def test_normalize_facility_type():
    assert normalize_facility_type(" Mill ") == "MILL"
    assert normalize_facility_type("Estate") == "ESTATE"

def test_normalize_spec_value():
    assert normalize_spec_value(" Eudr ") == "EUDR"
    assert normalize_spec_value("None") == "NONE"
    assert normalize_spec_value("NDPE") == "NDPE"

def test_normalize_trace_product():
    assert normalize_trace_product("CPO") == "CPO"
    assert normalize_trace_product("RBD PO") == "RBD PO"
    assert normalize_trace_product("PKO") == "PKO"
    assert normalize_trace_product("FFB") == "FFB"
    assert normalize_trace_product("Crude Palm Oil") == "CPO"

def test_safe_mean():
    s = pd.Series([1, 2, 3, None])
    assert safe_mean(s) == 2.0
    s_empty = pd.Series([None, None])
    assert safe_mean(s_empty, 5.0) == 5.0

def test_safe_median():
    s = pd.Series([1, 10, 100])
    assert safe_median(s) == 10.0
    s_empty = pd.Series([])
    assert safe_median(s_empty, 2.0) == 2.0

def test_round_days_up():
    assert round_days_up(1.1) == 2
    assert round_days_up(0) == 0
    assert round_days_up(-5.5) == 0

def test_is_valid_value():
    assert is_valid_value("hello") is True
    assert is_valid_value("nan") is False
    assert is_valid_value("None") is False
    assert is_valid_value("") is False
