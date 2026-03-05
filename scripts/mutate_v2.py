"""
V2 Mutation Engine
Loads config_v2.json, selects and mutates exactly one parameter according to strict rules,
enforces constraints, logs changes, and saves the updated configuration.
"""
import json
import random
import os
import sys
from datetime import datetime
from pathlib import Path

# Define mutation rules for each parameter
PARAM_RULES = {
    "rsi_period": {
        "type": "int",
        "steps": [-2, -1, 1, 2],
        "min": 7,
        "max": 30,
        "constraint": None
    },
    "buy_rsi": {
        "type": "int",
        "steps": [-5, 5],
        "min": 10,
        "max": 90,
        "constraint": None
    },
    "sell_rsi": {
        "type": "int",
        "steps": [-5, 5],
        "min": 10,
        "max": 90,
        "constraint": None
    },
    "macd_fast": {
        "type": "int",
        "steps": [-2, -1, 1, 2],
        "min": None,  # Will be handled by constraint
        "max": None,
        "constraint": "fast_slow_pair"
    },
    "macd_slow": {
        "type": "int",
        "steps": [-2, -1, 1, 2],
        "min": None,
        "max": None,
        "constraint": "fast_slow_pair"
    },
    "macd_signal": {
        "type": "int",
        "steps": [-2, -1, 1, 2],
        "min": 5,
        "max": 20,
        "constraint": None
    },
    "bb_length": {
        "type": "int",
        "steps": [-2, 2],
        "min": 5,
        "max": 50,
        "constraint": None
    },
    "bb_std": {
        "type": "float",
        "steps": [-0.1, 0.1],
        "min": 1.0,
        "max": 4.0,
        "constraint": None
    },
    "ema_fast": {
        "type": "int",
        "steps": [-2, -1, 1, 2],
        "min": None,
        "max": None,
        "constraint": "fast_slow_pair"
    },
    "ema_slow": {
        "type": "int",
        "steps": [-2, -1, 1, 2],
        "min": None,
        "max": None,
        "constraint": "fast_slow_pair"
    }
}

def load_config(config_path):
    """Load config_v2.json file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def save_config(config_path, config):
    """Save config_v2.json with proper formatting."""
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
        sys.exit(1)

def log_mutation(log_path, param_name, old_value, new_value, generation=None):
    """Append mutation details to evolution log."""
    # Ensure log directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if generation is not None:
        log_line = f"{timestamp} | Mutated {param_name}: {old_value} → {new_value} | generation={generation}\n"
    else:
        log_line = f"{timestamp} | Mutated {param_name}: {old_value} → {new_value}\n"
    
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_line)

def check_pair_constraint(param_name, new_value, other_param_name, other_value):
    """Check if fast < slow constraint is satisfied."""
    if param_name.endswith("_fast"):
        return new_value < other_value
    elif param_name.endswith("_slow"):
        return other_value < new_value
    return True

def mutate_parameter(config, param_name, generation=None):
    """Mutate a single parameter according to its rules."""
    if param_name not in config.get("parameters", {}):
        print(f"Parameter {param_name} not found in config")
        return False
    
    rules = PARAM_RULES[param_name]
    current_value = config["parameters"][param_name]
    
    # For parameters with fast/slow constraints, get the paired value
    other_param_name = None
    other_value = None
    if rules["constraint"] == "fast_slow_pair":
        if param_name == "macd_fast":
            other_param_name = "macd_slow"
        elif param_name == "macd_slow":
            other_param_name = "macd_fast"
        elif param_name == "ema_fast":
            other_param_name = "ema_slow"
        elif param_name == "ema_slow":
            other_param_name = "ema_fast"
        other_value = config["parameters"].get(other_param_name)
    
    # Try up to 20 attempts to find a valid mutation
    for attempt in range(20):
        # Select a random step
        step = random.choice(rules["steps"])
        
        # Compute candidate value
        if rules["type"] == "int":
            candidate = int(current_value + step)
        else:  # float
            candidate = round(current_value + step, 1)
        
        # Check min/max bounds
        if rules["min"] is not None and candidate < rules["min"]:
            continue
        if rules["max"] is not None and candidate > rules["max"]:
            continue
        
        # Check pair constraints
        if rules["constraint"] == "fast_slow_pair" and other_param_name and other_value is not None:
            if not check_pair_constraint(param_name, candidate, other_param_name, other_value):
                continue
        
        # All checks passed - apply mutation
        old_value = current_value
        config["parameters"][param_name] = candidate
        
        # Print and log the mutation
        print(f"Mutated {param_name}: {old_value} → {candidate}")
        
        # Log to evolution.log
        project_root = Path(__file__).parent.parent
        log_path = project_root / "user_data" / "logs" / "evolution.log"
        log_mutation(log_path, param_name, old_value, candidate, generation)
        
        return True
    
    # If we reach here, no valid mutation was found in 20 attempts
    print(f"Could not find valid mutation for {param_name} after 20 attempts")
    return False

def main():
    """Main mutation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="V2 Mutation Engine")
    parser.add_argument("--generation", type=int, help="Current generation number")
    args = parser.parse_args()
    
    # Set up paths
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config_v2.json"
    log_dir = project_root / "user_data" / "logs"
    
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Load configuration
    config = load_config(config_path)
    
    # Select a random parameter to mutate
    # All 10 parameters are always present in config_v2.json
    param_names = list(PARAM_RULES.keys())
    selected_param = random.choice(param_names)
    
    # Perform mutation
    success = mutate_parameter(config, selected_param, args.generation)
    
    if success:
        # Save updated configuration
        save_config(config_path, config)
    else:
        print("Mutation failed - configuration unchanged")

if __name__ == "__main__":
    main()
