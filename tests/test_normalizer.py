import pytest
from app.pipeline.normalizer import normalize_string

def test_normalize_string_basic():
    assert normalize_string("Hello World") == "hello world"

def test_normalize_string_special_chars():
    assert normalize_string("Amazon-Retail Inc.,") == "amazon retail inc"

def test_normalize_string_whitespace():
    assert normalize_string("  Myntra    Designs  \n  ") == "myntra designs"

def test_normalize_string_empty():
    assert normalize_string(None) == ""
    assert normalize_string("") == ""
    assert normalize_string("   ") == ""

def test_normalize_string_numbers():
    assert normalize_string("Order 123-A") == "order 123 a"

def test_normalize_string_reference():
    assert normalize_string("REF-123", is_reference=True) == "ref123"
    assert normalize_string("CUST 1", is_reference=True) == "cust1"
