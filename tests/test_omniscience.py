import pytest
import pandas as pd
import numpy as np
import inspect
import sys
import copy
from pathlib import Path
import importlib

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# --- 1. GLOBAL REPOSITORY CRAWL (IMPORT VALIDATION) ---
def discover_modules():
    modules = []
    
    for py_file in PROJECT_ROOT.rglob('*.py'):
        if any(skip in py_file.parts for skip in ['.venv', '__pycache__', '.git', 'tests']):
            continue
        
        # Construct module name relative to project root
        rel_path = py_file.relative_to(PROJECT_ROOT)
        module_name = ".".join(rel_path.with_suffix('').parts)
        modules.append(module_name)
            
    return modules

discovered_modules = discover_modules()

# Whitelist of files we expect to fail or want to skip during dynamic import/test
WHITELIST = [
    # Add any external freqtrade plugins or broken legacy scripts here
    "brain",  # WIP autonomous agents
]

@pytest.mark.parametrize("module_name", discovered_modules)
def test_global_module_import(module_name):
    """Verify that every Python file in the repository can be imported without crashing."""
    if any(wl in module_name for wl in WHITELIST):
        pytest.skip(f"Skipping whitelisted module: {module_name}")
        
    try:
        importlib.import_module(module_name)
    except Exception as e:
        pytest.fail(f"Omniscience Import Error in {module_name}: {e}")

# --- 2. OMNIPOTENT FUNCTION DISCOVERY ---
def get_all_functions():
    functions = []
    for module_name in discovered_modules:
        if any(wl in module_name for wl in WHITELIST):
            continue
        try:
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if obj.__module__ == module.__name__:
                    functions.append((module_name, name, obj))
        except:
            pass # Import errors are caught by test_global_module_import
    return functions

all_functions = get_all_functions()
all_functions_ids = [f"{m}.{n}" for m, n, _ in all_functions]

# --- 3. JSON DATA-GUARD ---
import json
from user_data.strategies.gp_blocks import BLOCK_REGISTRY

def discover_genomes():
    genomes = []
    # Find all genomes in the genomes directory
    genome_dir = PROJECT_ROOT / "user_data/strategies/genomes"
    if genome_dir.exists():
        for json_file in genome_dir.rglob('*.json'):
            genomes.append(json_file)
            
    # Include current_genome if it exists
    current_genome = PROJECT_ROOT / "user_data/current_genome.json"
    if current_genome.exists():
        genomes.append(current_genome)
        
    return genomes

discovered_genomes = discover_genomes()

@pytest.mark.parametrize("genome_file", discovered_genomes, ids=lambda x: x.name)
def test_json_genome_integrity(genome_file):
    """Verifies that all JSON genomes are structurally sound and use valid registry primitives."""
    with open(genome_file, 'r') as f:
        data = json.load(f)
        
    # Handle hall_of_fame array vs single genome dict
    if isinstance(data, list):
        for item in data:
            _validate_genome_structure(item)
    else:
        _validate_genome_structure(data)

def _validate_genome_structure(genome_data):
    # Some files wrap the trees in a "genome" key (like hall of fame entries)
    if "genome" in genome_data:
        genome_data = genome_data["genome"]
        
    assert "entry_tree" in genome_data, "Missing entry_tree in genome"
    assert "exit_tree" in genome_data, "Missing exit_tree in genome"
    
    _scan_tree_primitives(genome_data["entry_tree"])
    _scan_tree_primitives(genome_data["exit_tree"])

def _scan_tree_primitives(node):
    if not isinstance(node, dict):
        return
        
    if "primitive" in node:
        prim = node["primitive"]
        valid_primitives = list(BLOCK_REGISTRY['num'].keys()) + list(BLOCK_REGISTRY['bool_helper'].keys()) + list(BLOCK_REGISTRY['comparator'].keys())
        assert prim in valid_primitives, f"Primitive '{prim}' not found in BLOCK_REGISTRY!"
        
    if "children" in node:
        for child in node["children"]:
            _scan_tree_primitives(child)
            
    if "left" in node:
        _scan_tree_primitives(node["left"])
        
    if "right" in node:
        _scan_tree_primitives(node["right"])

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

@pytest.mark.parametrize("module_name, func_name, func", all_functions, ids=all_functions_ids)
def test_function_execution_safety(module_name, func_name, func, mock_df, mock_series):
    """
    Dynamically tests functions across the entire repository.
    Routes logic based on module origin or function naming conventions.
    """
    sig = inspect.signature(func)
    params = {}
    
    # Try to fulfill signature requirements
    if 'df' in sig.parameters or 'dataframe' in sig.parameters:
        params['df'] = mock_df
        if 'window' in sig.parameters: params['window'] = 14
        if 'std' in sig.parameters: params['std'] = 2.0
        if 'threshold' in sig.parameters: params['threshold'] = 1.5
    
    if 's1' in sig.parameters:
        params['s1'] = mock_series
        if 's2' in sig.parameters: params['s2'] = mock_series
        if 'threshold' in sig.parameters: params['threshold'] = 50.0
    
    if 'b1' in sig.parameters:
        params['b1'] = mock_series
        if 'b2' in sig.parameters: params['b2'] = mock_series
    if 'b' in sig.parameters:
        params['b'] = mock_series

    # GP Blocks Specific Logic
    if 'gp_blocks' in module_name:
        try:
            if func_name == 'register_block':
                pytest.skip("Skipping decorator")
            result = func(**params)
            if func_name != 'get_bollinger':
                assert isinstance(result, pd.Series), f"{func_name} did not return pd.Series"
                assert len(result) == 100, f"{func_name} returned wrong length series"
        except Exception as e:
            pytest.fail(f"Crash in gp_blocks.{func_name}(): {e}")
            
    # Evolution Engine Specific Logic
    elif 'evolution_engine' in module_name:
        dummy_tree = {
            "primitive": "GREATER_THAN",
            "left": {"primitive": "RSI", "parameters": {"window": 14}},
            "right": {"constant": 50.0}
        }
        dummy_genome = {"entry_tree": dummy_tree, "exit_tree": dummy_tree, "fitness": 0.0}
        
        try:
            if func_name in ['generate_num_node', 'generate_bool_node']:
                res = func(depth=0, max_depth=2)
                assert isinstance(res, dict)
            elif func_name == 'get_all_nodes':
                res = func(dummy_tree, "num")
                assert isinstance(res, list)
            elif func_name in ['apply_point_mutation', 'apply_structural_mutation']:
                func(copy.deepcopy(dummy_tree))
            elif func_name == 'get_similarity_hash':
                res = func(dummy_genome)
                assert isinstance(res, str)
            elif func_name == 'crossover_tree':
                t1, t2 = func(copy.deepcopy(dummy_tree), copy.deepcopy(dummy_tree))
                assert isinstance(t1, dict) and isinstance(t2, dict)
            else:
                pytest.skip(f"Skipping IO/Subprocess engine function: {func_name}")
        except Exception as e:
            pytest.fail(f"Crash in evolution_engine.{func_name}(): {e}")
            
    # Universal Utility Gate
    elif func_name.endswith(('_util', '_helper', '_engine')):
        try:
            # If it takes no required parameters, attempt a dry run
            required_params = [p for p in sig.parameters.values() if p.default == inspect.Parameter.empty]
            if not required_params:
                func()
            else:
                pytest.skip(f"Cannot auto-mock utility {func_name} with required args {required_params}")
        except Exception as e:
            pytest.fail(f"Crash in utility {module_name}.{func_name}(): {e}")
            
    else:
        pytest.skip(f"No auto-discovery logic mapped for {module_name}.{func_name}")
