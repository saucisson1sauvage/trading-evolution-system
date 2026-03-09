"""
Test script for AI Batch Generator
This script tests the validation and strike system without making actual API calls.
"""
import json
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.ai_batch_generator import (
    validate_tree_structure, 
    validate_batch,
    check_strikes,
    add_strike,
    KeyManager
)

def test_validation():
    """Test tree validation"""
    print("Testing tree validation...")
    
    # Valid tree
    valid_tree = {
        "operator": "AND",
        "children": [
            {
                "primitive": "VOLATILE",
                "parameters": {"window": 20, "threshold": 2.5}
            },
            {
                "primitive": "CROSS_UP",
                "left": {"primitive": "CLOSE"},
                "right": {"primitive": "EMA", "parameters": {"window": 10}}
            }
        ]
    }
    
    assert validate_tree_structure(valid_tree) == True, "Valid tree should pass"
    print("  ✓ Valid tree passes")
    
    # Invalid tree (non-existent primitive)
    invalid_tree = {
        "primitive": "NON_EXISTENT",
        "parameters": {"window": 10}
    }
    
    assert validate_tree_structure(invalid_tree) == False, "Invalid primitive should fail"
    print("  ✓ Invalid primitive fails")
    
    # Test batch validation
    print("\nTesting batch validation...")
    
    valid_batch = [
        {
            "type": "mutated_rank_1",
            "entry_tree": valid_tree,
            "exit_tree": {"primitive": "VOLATILE", "parameters": {"window": 10, "threshold": 1.5}}
        }
    ] * 5  # Create 5 identical objects
    
    assert validate_batch(valid_batch) == True, "Valid batch should pass"
    print("  ✓ Valid batch passes")
    
    # Invalid batch (wrong number of objects)
    invalid_batch = valid_batch[:3]  # Only 3 objects
    assert validate_batch(invalid_batch) == False, "Batch with wrong size should fail"
    print("  ✓ Batch with wrong size fails")
    
    print("\nAll validation tests passed!")

def test_key_manager():
    """Test the KeyManager class"""
    print("\nTesting KeyManager...")
    
    # Test initialization
    keys = ["key1", "key2"]
    manager = KeyManager(keys)
    
    # Test key selection based on generation parity
    assert manager.get_available_key(0) == "key1", "Even generation should use key1"
    assert manager.get_available_key(1) == "key2", "Odd generation should use key2"
    print("  ✓ Key selection based on parity works")
    
    # Test cooldown marking
    manager.mark_cooldown("key1")
    assert "key1" in manager.cooldowns, "key1 should be in cooldowns"
    print("  ✓ Cooldown marking works")
    
    # Test alternate key selection when primary is in cooldown
    # We need to mock time to test this properly
    import time
    original_time = time.time
    try:
        # Mock time to be within cooldown period
        test_time = 1000.0
        time.time = lambda: test_time
        
        # key1 is in cooldown, so even generation should use key2
        selected = manager.get_available_key(0)
        assert selected == "key2", "Should use alternate key when primary is in cooldown"
        print("  ✓ Alternate key selection works during cooldown")
        
        # Test cooldown expiration
        time.time = lambda: test_time + manager.cooldown_duration + 1
        manager.clear_expired_cooldowns()
        assert "key1" not in manager.cooldowns, "Expired cooldown should be cleared"
        print("  ✓ Cooldown expiration works")
        
    finally:
        time.time = original_time
    
    print("  KeyManager tests passed!")

def test_strike_system():
    """Test the strike system"""
    print("\nTesting strike system...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        
        # We need to mock the project_root in the module
        # This is a bit hacky, but works for testing
        import scripts.ai_batch_generator as mod
        original_root = mod.project_root
        mod.project_root = temp_root
        
        try:
            # Create necessary directories
            (temp_root / "user_data" / "logs").mkdir(parents=True)
            
            # Test with no strikes
            print("  Testing check_strikes with no strikes...")
            try:
                check_strikes()
                print("    ✓ No strikes passes")
            except SystemExit:
                print("    ✗ Should not exit with no strikes")
                raise
            
            # Add some strikes
            print("  Testing add_strike...")
            add_strike()
            
            # Verify strikes file was created
            strikes_path = temp_root / "user_data" / "logs" / "strikes.json"
            assert strikes_path.exists(), "Strikes file should exist"
            
            with open(strikes_path, 'r') as f:
                strikes = json.load(f)
            
            assert len(strikes) == 1, "Should have 1 strike"
            print("    ✓ Strike added successfully")
            
        finally:
            # Restore original project_root
            mod.project_root = original_root
    
    print("  Strike system tests passed!")

def main():
    """Run all tests"""
    print("Running AI Batch Generator tests...")
    print("=" * 50)
    
    try:
        test_validation()
        test_key_manager()
        test_strike_system()
        print("\n" + "=" * 50)
        print("All tests passed successfully!")
        return 0
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
