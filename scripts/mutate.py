import json
import random
import sys
from scripts.paths import PathResolver

def mutate():
    dna_path = PathResolver.get_strategies_path() / "dna.json"
    
    try:
        with open(dna_path, 'r') as f:
            dna = json.load(f)
    except Exception as e:
        print(f"Error loading DNA: {e}")
        sys.exit(1)

    params = dna.get("parameters", {})
    if not params:
        print("No parameters found in DNA.")
        sys.exit(1)

    param_to_mutate = random.choice(list(params.keys()))
    old_val = params[param_to_mutate]

    if param_to_mutate == "rsi_period":
        shift = random.choice([-2, -1, 1, 2])
        new_val = max(7, min(30, old_val + shift))
    elif param_to_mutate in ["buy_rsi", "sell_rsi"]:
        shift = random.choice([-5, 5])
        new_val = max(10, min(90, old_val + shift))
    else:
        # Default mutation for unknown parameters
        new_val = old_val

    if old_val == new_val:
        print(f"Mutation skipped for {param_to_mutate} (already at boundary: {old_val})")
    else:
        params[param_to_mutate] = new_val
        dna["parameters"] = params
        
        with open(dna_path, 'w') as f:
            json.dump(dna, f, indent=2)
        
        print(f"Mutated {param_to_mutate}: {old_val} -> {new_val}")

if __name__ == "__main__":
    mutate()
