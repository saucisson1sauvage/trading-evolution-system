import pytest
import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from scripts.evolution_engine import generate_bool_node, apply_point_mutation, get_similarity_hash

def test_generate_bool_node():
    node = generate_bool_node(depth=0, max_depth=2)
    assert isinstance(node, dict)
    # Could be operator or primitive
    assert "operator" in node or "primitive" in node

def test_apply_point_mutation():
    tree = {
        "primitive": "GREATER_THAN",
        "left": {"primitive": "RSI", "parameters": {"window": 14}},
        "right": {"constant": 50.0}
    }
    
    # Store old values
    old_window = tree["left"]["parameters"]["window"]
    old_constant = tree["right"]["constant"]
    
    # Mutate
    apply_point_mutation(tree)
    
    # Check if either changed (random choice)
    new_window = tree["left"]["parameters"]["window"]
    new_constant = tree["right"]["constant"]
    
    assert new_window != old_window or new_constant != old_constant

def test_get_similarity_hash():
    genome1 = {
        "entry_tree": {"primitive": "RSI", "parameters": {"window": 14}},
        "exit_tree": {"constant": 50.1}
    }
    genome2 = {
        "entry_tree": {"primitive": "RSI", "parameters": {"window": 14}},
        "exit_tree": {"constant": 50.4}
    }
    
    hash1 = get_similarity_hash(genome1)
    hash2 = get_similarity_hash(genome2)
    
    # 50.1 and 50.4 should both round to 50
    assert hash1 == hash2
