import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# We anticipate the existence of BLOCK_REGISTRY
from user_data.strategies.gp_blocks import BLOCK_REGISTRY
from user_data.strategies.GPTreeStrategy import GPTreeStrategy

@pytest.fixture
def mock_df():
    return pd.DataFrame({
        'open': np.random.uniform(2000, 3000, 100),
        'high': np.random.uniform(3000, 3100, 100),
        'low': np.random.uniform(1900, 2000, 100),
        'close': np.random.uniform(2000, 3000, 100),
        'volume': np.random.uniform(100, 1000, 100)
    })

@pytest.fixture
def strat():
    return GPTreeStrategy(config={'user_data_dir': str(PROJECT_ROOT / 'user_data')})

def test_num_and_bool_helper_blocks(mock_df, strat):
    for category in ['num', 'bool_helper']:
        assert category in BLOCK_REGISTRY, f"Category {category} missing from registry"
        for block_name in BLOCK_REGISTRY[category]:
            node = {"primitive": block_name, "parameters": {"window": 14, "std": 2.0, "threshold": 1.5}}
            res = strat.evaluate_node(node, mock_df)
            assert isinstance(res, pd.Series), f"{block_name} should return pd.Series, got {type(res)}"
            assert len(res) == len(mock_df)

def test_comparator_blocks(mock_df, strat):
    assert 'comparator' in BLOCK_REGISTRY
    for comp_name in BLOCK_REGISTRY['comparator']:
        node = {
            "primitive": comp_name,
            "left": {"primitive": "RSI", "parameters": {"window": 14}},
            "right": {"constant": 50.0}
        }
        res = strat.evaluate_node(node, mock_df)
        assert isinstance(res, pd.Series)
        assert len(res) == len(mock_df)

def test_operator_blocks(mock_df, strat):
    assert 'operator' in BLOCK_REGISTRY
    for op_name in BLOCK_REGISTRY['operator']:
        if op_name == "NOT":
            node = {"operator": "NOT", "children": [{"primitive": "TRENDING_UP", "parameters": {"window": 10}}]}
        else:
            node = {"operator": op_name, "children": [
                {"primitive": "TRENDING_UP", "parameters": {"window": 10}},
                {"primitive": "VOLUME_SPIKE", "parameters": {"window": 10}}
            ]}
        res = strat.evaluate_node(node, mock_df)
        assert isinstance(res, pd.Series)
        assert len(res) == len(mock_df)
