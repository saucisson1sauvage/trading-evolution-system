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

    # 20% chance for structural mutation
    if random.random() < 0.2:
        # Structural mutation: add or remove a block
        active_blocks = dna.get("active_blocks", [])
        available_blocks = ["rsi_simple", "macd_simple"]
        
        # Ensure active_blocks is never empty
        if len(active_blocks) == 0:
            # Add a random block
            block_to_add = random.choice(available_blocks)
            active_blocks.append(block_to_add)
            dna["active_blocks"] = active_blocks
            print(f"Structural mutation: Added {block_to_add} to Genome (active_blocks was empty)")
            
            # Add default parameters for the new block
            params = dna.get("parameters", {})
            if block_to_add == "macd_simple":
                params.setdefault("macd_fast", 12)
                params.setdefault("macd_slow", 26)
                params.setdefault("macd_signal", 9)
            elif block_to_add == "rsi_simple":
                params.setdefault("rsi_period", 14)
                params.setdefault("buy_rsi", 30)
                params.setdefault("sell_rsi", 70)
            dna["parameters"] = params
        else:
            # Decide to add or remove
            if random.random() < 0.5:
                # Add a block
                # Find blocks not in active_blocks
                possible_additions = [b for b in available_blocks if b not in active_blocks]
                if possible_additions:
                    block_to_add = random.choice(possible_additions)
                    active_blocks.append(block_to_add)
                    dna["active_blocks"] = active_blocks
                    print(f"Structural mutation: Added {block_to_add} to Genome")
                    
                    # Add default parameters for the new block
                    params = dna.get("parameters", {})
                    if block_to_add == "macd_simple":
                        params.setdefault("macd_fast", 12)
                        params.setdefault("macd_slow", 26)
                        params.setdefault("macd_signal", 9)
                    elif block_to_add == "rsi_simple":
                        params.setdefault("rsi_period", 14)
                        params.setdefault("buy_rsi", 30)
                        params.setdefault("sell_rsi", 70)
                    dna["parameters"] = params
                else:
                    print("Structural mutation: No new blocks to add")
            else:
                # Remove a block, but ensure active_blocks is never empty
                if len(active_blocks) > 1:
                    block_to_remove = random.choice(active_blocks)
                    active_blocks.remove(block_to_remove)
                    dna["active_blocks"] = active_blocks
                    print(f"Structural mutation: Removed {block_to_remove} from Genome")
                else:
                    print("Structural mutation: Cannot remove last block (active_blocks would be empty)")
    else:
        # Parameter mutation
        params = dna.get("parameters", {})
        if not params:
            print("No parameters found in DNA.")
            sys.exit(1)

        param_to_mutate = random.choice(list(params.keys()))
        old_val = params[param_to_mutate]

        # Define mutation ranges for each parameter
        if param_to_mutate == "rsi_period":
            shift = random.choice([-2, -1, 1, 2])
            new_val = max(7, min(30, old_val + shift))
        elif param_to_mutate in ["buy_rsi", "sell_rsi"]:
            shift = random.choice([-5, 5])
            new_val = max(10, min(90, old_val + shift))
        elif param_to_mutate in ["macd_fast", "macd_slow", "macd_signal"]:
            shift = random.choice([-2, -1, 1, 2])
            # Ensure reasonable values
            if param_to_mutate == "macd_fast":
                new_val = max(8, min(20, old_val + shift))
            elif param_to_mutate == "macd_slow":
                new_val = max(20, min(40, old_val + shift))
            else:  # macd_signal
                new_val = max(5, min(15, old_val + shift))
        else:
            # Default mutation for unknown parameters
            new_val = old_val

        if old_val == new_val:
            print(f"Parameter mutation skipped for {param_to_mutate} (already at boundary: {old_val})")
        else:
            params[param_to_mutate] = new_val
            dna["parameters"] = params
            print(f"Parameter mutation: {param_to_mutate}: {old_val} -> {new_val}")

    # Save the mutated DNA
    with open(dna_path, 'w') as f:
        json.dump(dna, f, indent=2)

if __name__ == "__main__":
    mutate()
