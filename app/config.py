"""
Configuration for the reconciliation engine.
These thresholds and signal weights are tuned on the dev set and MUST BE FROZEN
before evaluating on the held-out test set.
"""

# Signal Weights (Maximum possible score contributions)
WEIGHT_REFERENCE_ID = 50.0
WEIGHT_AMOUNT_EXACT = 35.0
WEIGHT_AMOUNT_TOLERANCE = 10.0
WEIGHT_DATE_EXACT = 15.0
WEIGHT_DATE_PROXIMITY = 5.0
WEIGHT_CUSTOMER_ID = 10.0
WEIGHT_DESC_MATCH = 10.0

# Tolerances
TOLERANCE_AMOUNT_PERCENT = 0.005  # 0.5%
TOLERANCE_DATE_DAYS = 2

# Contradiction constraints
CONTRADICTION_AMOUNT_PERCENT = 0.10  # 10%
CONTRADICTION_DATE_DAYS = 7

# Engine routing thresholds
THRESHOLD_AUTO = 90.0
THRESHOLD_REVIEW = 70.0
THRESHOLD_MIN_SCORE = 20.0
MARGIN_SEPARATION = 15.0

import hashlib
import json

def get_config_hash() -> str:
    """
    Returns a deterministic SHA-256 hash of all configuration values
    to uniquely identify the frozen engine configuration for a run.
    """
    # Collect all uppercase variables in this module
    config_dict = {
        k: v for k, v in globals().items() 
        if k.isupper() and not k.startswith('_')
    }
    
    # Sort keys for deterministic JSON serialization
    config_json = json.dumps(config_dict, sort_keys=True)
    
    return hashlib.sha256(config_json.encode('utf-8')).hexdigest()[:16]
