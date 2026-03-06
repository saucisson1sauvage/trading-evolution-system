#!/usr/bin/env python3
"""
Deep-diagnostic stress test to verify 100% integrity of the Universal Block Registry.
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging

# Add project root to path
PROJECT_ROOT = Path("/home/saus/crypto-crew-4.0")
sys.path.append(str(PROJECT_ROOT / "user_data/strategies"))

# Import the strategy and blocks
try:
    from gp_blocks import *
    from GPTreeStrategy import GPTreeStrategy
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def create_mock_dataframe(rows=100):
    """Generate realistic OHLCV data for testing."""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=rows, freq='5min')
    close = np.cumprod(1 + np.random.randn(rows) * 0.01) * 100
    open_price = close * (1 + np.random.randn(rows) * 0.005)
    high = np.maximum(open_price, close) * (1 + np.random.rand(rows) * 0.02)
    low = np.minimum(open_price, close) * (1 - np.random.rand(rows) * 0.02)
    volume = np.random.randint(1000, 10000, size=rows)
    
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    return df

def define_block_registry():
    """Define the registry based on gp_blocks.py functions."""
    registry = {
        'num': ['RSI', 'EMA', 'SMA', 'BB_UPPER', 'BB_MIDDLE', 'BB_LOWER'],
        'bool_helper': ['TRENDING_UP', 'TRENDING_DOWN', 'VOLATILE', 'VOLUME_SPIKE'],
        'comparator': ['GREATER_THAN', 'LESS_THAN', 'CROSS_UP', 'CROSS_DOWN'],
        'operator': ['AND', 'OR', 'NOT']
    }
    return registry

def test_num_and_bool_helper_blocks(strategy, df):
    """Test numeric and boolean helper blocks."""
    registry = define_block_registry()
    print("🧪 Testing NUM & BOOL_HELPER blocks...")
    
    all_blocks = registry['num'] + registry['bool_helper']
    for block_name in all_blocks:
        try:
            # Prepare parameters based on block type
            params = {"window": 14}
            if "BB" in block_name:
                params["std"] = 2.0
            if block_name == "VOLATILE":
                params["threshold"] = 1.5
            if block_name == "VOLUME_SPIKE":
                params["threshold"] = 2.0
            
            node = {"primitive": block_name, "parameters": params}
            result = strategy.evaluate_node(node, df)
            
            # Assertions
            assert isinstance(result, pd.Series), f"{block_name}: Result is not a Series"
            assert len(result) == len(df), f"{block_name}: Length mismatch"
            print(f"  ✅ {block_name}")
            
        except Exception as e:
            print(f"  ❌ {block_name}: {e}")
            raise

def test_comparator_blocks(strategy, df):
    """Test comparator blocks with nested nodes."""
    registry = define_block_registry()
    print("\n🧪 Testing COMPARATOR blocks...")
    
    for comp_name in registry['comparator']:
        try:
            node = {
                "primitive": comp_name,
                "left": {"primitive": "RSI", "parameters": {"window": 14}},
                "right": {"constant": 50.0}
            }
            result = strategy.evaluate_node(node, df)
            
            assert isinstance(result, pd.Series), f"{comp_name}: Result is not a Series"
            assert len(result) == len(df), f"{comp_name}: Length mismatch"
            # Comparators should return boolean series
            assert result.dtype == bool, f"{comp_name}: Expected bool dtype, got {result.dtype}"
            print(f"  ✅ {comp_name}")
            
        except Exception as e:
            print(f"  ❌ {comp_name}: {e}")
            raise

def test_operator_blocks(strategy, df):
    """Test operator blocks with proper arity."""
    print("\n🧪 Testing OPERATOR blocks...")
    
    # Test AND/OR with 2 children
    for op in ['AND', 'OR']:
        try:
            node = {
                "operator": op,
                "children": [
                    {"primitive": "TRENDING_UP", "parameters": {"window": 20}},
                    {"primitive": "VOLUME_SPIKE", "parameters": {"window": 20, "threshold": 2.0}}
                ]
            }
            result = strategy.evaluate_node(node, df)
            
            assert isinstance(result, pd.Series), f"{op}: Result is not a Series"
            assert len(result) == len(df), f"{op}: Length mismatch"
            assert result.dtype == bool, f"{op}: Expected bool dtype, got {result.dtype}"
            print(f"  ✅ {op} (2 children)")
            
        except Exception as e:
            print(f"  ❌ {op}: {e}")
            raise
    
    # Test NOT with 1 child
    try:
        node = {
            "operator": "NOT",
            "children": [
                {"primitive": "TRENDING_DOWN", "parameters": {"window": 20}}
            ]
        }
        result = strategy.evaluate_node(node, df)
        
        assert isinstance(result, pd.Series), f"NOT: Result is not a Series"
        assert len(result) == len(df), f"NOT: Length mismatch"
        assert result.dtype == bool, f"NOT: Expected bool dtype, got {result.dtype}"
        print(f"  ✅ NOT (1 child)")
        
    except Exception as e:
        print(f"  ❌ NOT: {e}")
        raise

def test_constant_node(strategy, df):
    """Test constant nodes."""
    print("\n🧪 Testing CONSTANT nodes...")
    
    try:
        node = {"constant": 42.5}
        result = strategy.evaluate_node(node, df)
        
        assert isinstance(result, pd.Series), f"Constant: Result is not a Series"
        assert len(result) == len(df), f"Constant: Length mismatch"
        # All values should be the constant
        assert (result == 42.5).all(), f"Constant: Not all values are 42.5"
        print(f"  ✅ Constant")
        
    except Exception as e:
        print(f"  ❌ Constant: {e}")
        raise

def main():
    print("🚀 STARTING UNIVERSAL BLOCK REGISTRY INTEGRITY TEST")
    print("=" * 60)
    
    # Create mock data
    df = create_mock_dataframe(100)
    print(f"📊 Created mock DataFrame with {len(df)} rows")
    
    # Instantiate strategy with minimal config
    config = {
        'user_data_dir': str(PROJECT_ROOT / "user_data"),
        'stake_currency': 'USDT'
    }
    try:
        strat = GPTreeStrategy(config=config)
        print("✅ Strategy instantiated")
    except Exception as e:
        print(f"❌ Failed to instantiate strategy: {e}")
        sys.exit(1)
    
    # Run all tests
    try:
        test_constant_node(strat, df)
        test_num_and_bool_helper_blocks(strat, df)
        test_comparator_blocks(strat, df)
        test_operator_blocks(strat, df)
        
        print("\n" + "=" * 60)
        print("✅ ALL REGISTRY BLOCKS VERIFIED AND TYPE-SAFE.")
        print("🎉 Integrity test PASSED!")
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
