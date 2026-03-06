import pytest
import pandas as pd
import numpy as np
import inspect
import sys
import copy
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# Import the modules we want to dynamically test
import user_data.strategies.gp_blocks as gp_blocks
import scripts.evolution_engine as evolution_engine
import user_data.strategies.GPTreeStrategy as GPTreeStrategy

@pytest.fixture(scope="module")
def mock_df():
    """Provides a standard 100-row OHLCV DataFrame for testing."""
    return pd.DataFrame({
        'open': np.random.uniform(2000, 3000, 100),
        'high': np.random.uniform(3000, 3100, 100),
        'low': np.random.uniform(1900, 2000, 100),
        'close': np.random.uniform(2000, 3000, 100),
        'volume': np.random.uniform(100, 1000, 100)
    })

@pytest.fixture(scope="module")
def mock_series():
    """Provides a standard 100-row Boolean Series for testing logic operators."""
    return pd.Series(np.random.choice([True, False], size=100))

def get_functions_from_module(module):
    """Uses introspection to find all callable functions defined IN the module (not imported)."""
    functions = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        # Ensure we only test functions defined in the target module, not built-ins or imports
        if obj.__module__ == module.__name__:
            functions.append((name, obj))
    return functions

# Dynamically gather all functions
gp_blocks_funcs = get_functions_from_module(gp_blocks)
evolution_engine_funcs = get_functions_from_module(evolution_engine)

@pytest.mark.parametrize("name, func", gp_blocks_funcs)
def test_gp_blocks_omniscience(name, func, mock_df, mock_series):
    """
    Dynamically tests every function in gp_blocks.py.
    It reads the signature and attempts to provide the correct mock data.
    """
    sig = inspect.signature(func)
    params = {}
    
    # 1. Provide a DataFrame if requested
    if 'df' in sig.parameters or 'dataframe' in sig.parameters:
        params['df'] = mock_df
        # Provide default fallback params for indicators
        if 'window' in sig.parameters: params['window'] = 14
        if 'std' in sig.parameters: params['std'] = 2.0
        if 'threshold' in sig.parameters: params['threshold'] = 1.5
    
    # 2. Provide Series for Comparators (e.g., greater_than(s1, s2))
    elif 's1' in sig.parameters:
        params['s1'] = mock_series
        if 's2' in sig.parameters: params['s2'] = mock_series
        if 'threshold' in sig.parameters: params['threshold'] = 50.0
    
    # 3. Provide Series for Logic Operators (e.g., and_op(b1, b2))
    elif 'b1' in sig.parameters:
        params['b1'] = mock_series
        if 'b2' in sig.parameters: params['b2'] = mock_series
    elif 'b' in sig.parameters: # For not_op
        params['b'] = mock_series

    # Execute the function
    try:
        if name == 'register_block':
            pytest.skip("Skipping decorator function")
            return
            
        result = func(**params)
        
        # Verify output integrity
        if name != 'get_bollinger' and name != 'register_block': # register_block is a decorator, bollinger returns a tuple
            assert isinstance(result, pd.Series), f"{name} did not return a pd.Series"
            assert len(result) == 100, f"{name} returned wrong length series"
            
    except Exception as e:
        pytest.fail(f"Omniscience caught a crash in gp_blocks.{name}(): {e}")

@pytest.mark.parametrize("name, func", evolution_engine_funcs)
def test_evolution_engine_omniscience(name, func):
    """
    Dynamically tests core functions in evolution_engine.py using mock AST data.
    """
    sig = inspect.signature(func)
    
    dummy_tree = {
        "primitive": "GREATER_THAN",
        "left": {"primitive": "RSI", "parameters": {"window": 14}},
        "right": {"constant": 50.0}
    }
    
    dummy_genome = {
        "entry_tree": dummy_tree,
        "exit_tree": dummy_tree,
        "fitness": 0.0
    }

    try:
        if name == 'generate_num_node' or name == 'generate_bool_node':
            res = func(depth=0, max_depth=2)
            assert isinstance(res, dict)
            
        elif name == 'get_all_nodes':
            res = func(dummy_tree, "num")
            assert isinstance(res, list)
            
        elif name == 'apply_point_mutation' or name == 'apply_structural_mutation':
            func(copy.deepcopy(dummy_tree)) # Should execute without KeyError
            
        elif name == 'get_similarity_hash':
            res = func(dummy_genome)
            assert isinstance(res, str)
            
        elif name == 'crossover_tree':
            t1, t2 = func(copy.deepcopy(dummy_tree), copy.deepcopy(dummy_tree))
            assert isinstance(t1, dict) and isinstance(t2, dict)
            
        elif name in ['run_evolution_round', 'run_single_backtest', 'run_loop', 'save_to_vault', 'log_aider']:
            # Skip heavy integration functions that require Freqtrade binary execution or file IO
            pytest.skip(f"Skipping IO/Subprocess function: {name}")
            
        else:
            pytest.skip(f"No mock data mapped for: {name}")
            
    except Exception as e:
        pytest.fail(f"Omniscience caught a crash in evolution_engine.{name}(): {e}")
