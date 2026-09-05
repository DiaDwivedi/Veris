import json
import os
import shutil
import pytest
from unittest.mock import patch
from app.pipeline.evaluate import evaluate

def test_evaluate_produces_json_artifact(tmp_path):
    # We patch os.makedirs and the file writing to write to a temp dir
    # But evaluating on real dev set data might fail if data is missing
    # Let's mock the load functions to return small static data
    
    with patch('app.pipeline.evaluate.load_transactions') as mock_lt, \
         patch('app.pipeline.evaluate.load_orders') as mock_lo, \
         patch('app.pipeline.evaluate.load_ground_truth') as mock_lgt, \
         patch('app.pipeline.evaluate.os.makedirs') as mock_md, \
         patch('app.pipeline.evaluate.open') as mock_open:
        
        # We don't even need to mock data heavily if we just want to ensure it runs
        # But let's provide empty lists just in case
        mock_lt.return_value = []
        mock_lo.return_value = []
        mock_lgt.return_value = {}
        
        # run evaluate
        evaluate()
        
        # verify makedirs called
        mock_md.assert_called_with("evaluation/results", exist_ok=True)
        
        # verify open called for json
        assert mock_open.call_count == 1
        args, kwargs = mock_open.call_args
        assert "evaluation/results/evaluation_run_" in args[0]
        assert args[0].endswith(".json")

def test_evaluate_real_run_artifact_structure():
    # Let's run it fully if data exists, and parse the json
    if not os.path.exists("data/dev_transactions.csv"):
        pytest.skip("Data not available")
        
    evaluate()
    
    # Check the latest file in evaluation/results/
    results_dir = "evaluation/results"
    files = [f for f in os.listdir(results_dir) if f.endswith(".json")]
    files.sort()
    latest_file = os.path.join(results_dir, files[-1])
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        artifact = json.load(f)
        
    assert "metadata" in artifact
    assert "metrics" in artifact
    assert "scenario_breakdown" in artifact
    assert "details" in artifact
    
    # Official metrics required
    metrics = artifact["metrics"]
    assert "auto_precision_percentage" in metrics
    assert "auto_precision_correct" in metrics
    assert "auto_precision_total" in metrics
    assert "auto_match_recall" in metrics
    assert "candidate_recall" in metrics
    assert "auto_rate" in metrics
    assert "review_rate" in metrics
    assert "unmatched_rate" in metrics
    
    # Ensure no confusion matrix or F1 or ROC
    assert "confusion_matrix" not in metrics
    assert "f1" not in metrics
    assert "roc" not in metrics
    
    # Check pair and decision correctness
    if len(artifact["details"]) > 0:
        detail = artifact["details"][0]
        assert "is_pair_correct" in detail
        assert "is_decision_correct" in detail
