import random
import json
import os
import copy
import logging
import subprocess
import re
import math
import datetime
import uuid
import time
from typing import Dict, Any, List, Tuple
from pathlib import Path
import sys

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRATEGY_DIR = PROJECT_ROOT / "user_data/strategies"
GENOME_DIR = STRATEGY_DIR / "genomes"
POPULATION_FILE = STRATEGY_DIR / "population.json"
STATE_FILE = STRATEGY_DIR / "state.json"
CURRENT_GENOME_FILE = PROJECT_ROOT / "user_data/current_genome.json"
LOG_FILE = PROJECT_ROOT / "user_data/logs/evolution.log"
VAULT_FILE = GENOME_DIR / "hall_of_fame.json"
AIDER_LOG_FILE = PROJECT_ROOT / "user_data/logs/aider_debug.log"

sys.path.append(str(PROJECT_ROOT))

def log_aider(message: str):
    """Log high-signal events for Aider context."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(AIDER_LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    # Keep it light: only last 500 lines
    lines = []
    if AIDER_LOG_FILE.exists():
        with open(AIDER_LOG_FILE, 'r') as f:
            lines = f.readlines()
        if len(lines) > 500:
            with open(AIDER_LOG_FILE, 'w') as f:
                f.writelines(lines[-500:])

# Load .env
if (PROJECT_ROOT / ".env").exists():
    with open(PROJECT_ROOT / ".env") as f:
        for line in f:
            if '=' in line:
                parts = line.strip().split('=', 1)
                if len(parts) == 2:
                    os.environ[parts[0]] = parts[1]

from user_data.strategies.gp_blocks import BLOCK_REGISTRY

# Grammar Definitions (Dynamically loaded from BLOCK_REGISTRY)
BOOL_PRIMITIVES = list(BLOCK_REGISTRY['comparator'].keys())
BOOL_OPERATORS = list(BLOCK_REGISTRY['operator'].keys())
BOOL_HELPERS = list(BLOCK_REGISTRY['bool_helper'].keys())
NUM_INDICATORS = list(BLOCK_REGISTRY['num'].keys())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, mode='a'), logging.StreamHandler()]
)

def generate_num_node(depth: int, max_depth: int) -> Dict[str, Any]:
    if depth >= max_depth or random.random() < 0.3:
        if random.random() < 0.7:
             name = random.choice(NUM_INDICATORS)
             params = {"window": random.randint(7, 50)}
             if "BB" in name:
                 params["std"] = round(random.uniform(1.5, 3.0), 1)
             return {"primitive": name, "parameters": params}
        else:
             return {"constant": round(random.uniform(20, 80), 2)}
    
    name = random.choice(NUM_INDICATORS)
    params = {"window": random.randint(7, 50)}
    if "BB" in name:
        params["std"] = round(random.uniform(1.5, 3.0), 1)
    return {"primitive": name, "parameters": params}

def generate_bool_node(depth: int, max_depth: int) -> Dict[str, Any]:
    if depth < max_depth and random.random() < 0.5:
        op = random.choice(BOOL_OPERATORS)
        if op == "NOT":
            return {"operator": "NOT", "children": [generate_bool_node(depth + 1, max_depth)]}
        else:
            return {"operator": op, "children": [generate_bool_node(depth + 1, max_depth), generate_bool_node(depth + 1, max_depth)]}
    elif random.random() < 0.4:
        name = random.choice(BOOL_HELPERS)
        params = {"window": random.randint(7, 50)}
        if name == "VOLATILE":
             params["threshold"] = round(random.uniform(1.1, 2.5), 2)
        return {"primitive": name, "parameters": params}
    else:
        return {
            "primitive": random.choice(BOOL_PRIMITIVES),
            "left": generate_num_node(depth + 1, max_depth),
            "right": generate_num_node(depth + 1, max_depth)
        }

def get_all_nodes(node: Dict[str, Any], node_type: str) -> List[Dict[str, Any]]:
    nodes = []
    current_type = None
    if "operator" in node or ("primitive" in node and (node["primitive"] in BOOL_PRIMITIVES or node["primitive"] in BOOL_HELPERS)):
        current_type = "bool"
    elif "constant" in node or ("primitive" in node and node["primitive"] in NUM_INDICATORS):
        current_type = "num"
        
    if current_type == node_type:
        nodes.append(node)
        
    if "children" in node:
        for child in node["children"]:
            nodes.extend(get_all_nodes(child, node_type))
    if "left" in node:
        nodes.extend(get_all_nodes(node["left"], node_type))
    if "right" in node:
        nodes.extend(get_all_nodes(node["right"], node_type))
        
    return nodes

def apply_point_mutation(tree: Dict[str, Any]):
    nodes = get_all_nodes(tree, "num")
    if not nodes: return
    random.shuffle(nodes)
    for target in nodes:
        if "constant" in target:
            shift = target["constant"] * random.uniform(0.05, 0.10) * random.choice([-1, 1])
            target["constant"] = round(max(0.1, target["constant"] + shift), 2)
            break
        elif "parameters" in target:
            mutated = False
            if "window" in target["parameters"]:
                shift = int(target["parameters"]["window"] * random.uniform(0.05, 0.10) * random.choice([-1, 1]))
                if shift == 0: shift = random.choice([-1, 1])
                target["parameters"]["window"] = max(2, target["parameters"]["window"] + shift)
                mutated = True
            if "std" in target["parameters"]:
                shift = target["parameters"]["std"] * random.uniform(0.05, 0.10) * random.choice([-1, 1])
                target["parameters"]["std"] = round(max(0.1, target["parameters"]["std"] + shift), 2)
                mutated = True
            if mutated:
                break

def apply_structural_mutation(tree: Dict[str, Any]):
    types = ["bool", "num"]
    random.shuffle(types)
    for t in types:
        nodes = get_all_nodes(tree, t)
        if nodes:
            target = random.choice(nodes)
            new_sub = generate_bool_node(0, 2) if t == "bool" else generate_num_node(0, 2)
            target.clear()
            target.update(new_sub)
            break

def get_similarity_hash(genome: dict) -> str:
    """Creates a structural hash of the genome by rounding all floats to integers, preventing 99% identical clones."""
    raw_str = json.dumps({"entry": genome.get("entry_tree", {}), "exit": genome.get("exit_tree", {})})
    return re.sub(r'(\d+\.\d+)', lambda m: str(round(float(m.group(1)))), raw_str)

def save_to_vault(king: dict):
    vault = []
    if VAULT_FILE.exists():
        try:
            with open(VAULT_FILE, 'r') as f:
                vault = json.load(f)
        except Exception:
            pass
            
    # Highlander: Only one per lineage
    lineage_found = False
    for i, v in enumerate(vault):
        if v.get("lineage_id") == king.get("lineage_id"):
            lineage_found = True
            if king.get("fitness", 0.0) > v.get("fitness", 0.0):
                vault[i] = copy.deepcopy(king)
                vault.sort(key=lambda x: x.get("fitness", 0.0), reverse=True)
                with open(VAULT_FILE, 'w') as f:
                    json.dump(vault, f, indent=2)
                logging.info(f"  > VAULT UPDATED (Lineage improved). Top fitness: {vault[0].get('fitness', 0.0):.4f}")
            return
            
    if not lineage_found:
        vault.append(copy.deepcopy(king))
        
    vault.sort(key=lambda x: x.get("fitness", 0.0), reverse=True)
    vault = vault[:3]
    
    VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(VAULT_FILE, 'w') as f:
        json.dump(vault, f, indent=2)
    logging.info(f"  > VAULT UPDATED. Top strategy fitness: {vault[0].get('fitness', 0.0):.4f}")

def run_single_backtest(genome: dict, timerange: str) -> Dict[str, float]:
    CURRENT_GENOME_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CURRENT_GENOME_FILE, 'w') as f:
        json.dump(genome, f, indent=2)
    
    freqtrade_bin = str(Path(sys.executable).parent / "freqtrade")
    
    command = [
        freqtrade_bin, "backtesting",
        "--strategy", "GPTreeStrategy",
        "--timerange", timerange,
        "--config", str(PROJECT_ROOT / "config.json"),
        "--userdir", str(PROJECT_ROOT / "user_data"),
        "--cache", "none"
    ]
    try:
        res = subprocess.run(command, capture_output=True, text=True, timeout=60)
        output = res.stdout
        
        sum_match = re.search(r"GPTreeStrategy\s+[|│]\s+(\d+)\s+[|│]\s+([\d\.-]+)\s+[|│]\s+([\d\.-]+)\s+[|│]\s+([\d\.-]+)", output)
        sharpe_match = re.search(r"Sharpe\s+[|│]\s+([\d\.-]+)", output)
        dd_match = re.search(r"Absolute drawdown\s+[|│]\s+[\d\.-]+\s+USDT\s+\(([\d\.-]+)%\)", output)
        
        results = {"trades": 0, "profit": 0.0, "sharpe": -5.0, "drawdown": 100.0}
        if sum_match:
            results["trades"] = int(sum_match.group(1))
            results["profit"] = float(sum_match.group(4))
        if sharpe_match:
            results["sharpe"] = float(sharpe_match.group(1))
        if dd_match:
            results["drawdown"] = float(dd_match.group(1))
            
        return results
    except Exception:
        return {"trades": 0, "profit": 0.0, "sharpe": -5.0, "drawdown": 100.0}

def run_evolution_round(genome: dict) -> float:
    # Use 5 Fixed Regimes (No internet/download required)
    periods = [
        "20250101-20250201", # Recent-ish
        "20241105-20241205", # Bull
        "20250110-20250125", # Bear
        "20240804-20240808", # Crash
        "20241215-20250105"  # Sideways
    ]
    
    total_profit = 0.0
    total_trades = 0
    total_sharpe = 0.0
    max_drawdown = 0.0
    
    for tr in periods:
        res = run_single_backtest(genome, tr)
        total_profit += res["profit"]
        total_trades += res["trades"]
        total_sharpe += max(0, res["sharpe"])
        max_drawdown = max(max_drawdown, res["drawdown"])
        
    avg_sharpe = total_sharpe / len(periods)
    
    if total_trades < 10 or total_profit <= 0:
        fitness = 0.0
        logging.info(f"  > FAIL: Aggregated Trades: {total_trades}, Profit: {total_profit}% -> Fitness: 0.0000")
    else:
        s = max(0.01, avg_sharpe)
        fitness = (total_profit * s * math.log(total_trades + 1)) / (1 + max_drawdown)
        logging.info(f"  > SUCCESS: Aggregated Trades: {total_trades}, Profit: {total_profit}%, Avg Sharpe: {avg_sharpe:.2f}, Max DD: {max_drawdown}% -> Fitness: {fitness:.4f}")
        
    return fitness

def create_fresh_individual(status="outsider"):
    return {
        "lineage_id": str(uuid.uuid4()),
        "entry_tree": generate_bool_node(0, 3),
        "exit_tree": generate_bool_node(0, 3),
        "fitness": -1.0,
        "generation_age": 0,
        "debuff_active_gens": 0,
        "status": status
    }

def calculate_debuffed_fitness(genome: dict, king_age: int) -> float:
    if genome.get("status") == "king":
        return genome.get("fitness", 0.0)
    
    if king_age <= 10:
        r = 0.05
    elif king_age >= 1000:
        r = 0.01
    else:
        r = 0.05 - ((king_age - 10) / 990.0) * 0.04
        
    debuff_active_gens = genome.get("debuff_active_gens", 0)
    penalty = r * debuff_active_gens
    
    return genome.get("fitness", 0.0) * max(0.0, (1.0 - penalty))

def check_retirement(genome: dict, outsiders_max_fitness: float):
    if genome.get("status") in ["candidate", "mutant"]:
        if genome.get("debuffed_fitness", 0.0) < outsiders_max_fitness:
            genome["status"] = "retired"
            logging.info(f"  > Lineage {genome.get('lineage_id', 'unknown')[:8]} RETIRED due to low debuffed fitness.")

def generate_ai_outsider(type: str) -> Dict[str, Any]:
    """Generate a fresh random genome for AI outsiders."""
    if type == "guided":
        # For now, same as alien, but can be enhanced later
        pass
    # Generate fresh individual
    individual = create_fresh_individual("outsider")
    individual["lineage_id"] = str(uuid.uuid4())
    individual["status"] = "outsider"
    individual["debuff_active_gens"] = 0
    individual["fitness"] = -1.0
    log_aider(f"Generated {type} outsider with lineage {individual['lineage_id'][:8]}")
    return individual

def load_vault() -> List[Dict[str, Any]]:
    """Load and sort the Vault (hall_of_fame.json)."""
    vault = []
    if VAULT_FILE.exists():
        try:
            with open(VAULT_FILE, 'r') as f:
                vault = json.load(f)
            # Sort by fitness in descending order
            vault.sort(key=lambda x: x.get("fitness", 0.0), reverse=True)
        except Exception as e:
            logging.error(f"Failed to load Vault: {e}")
    return vault

def run_loop(gens=50):
    logging.info(f"STARTING 6-SLOT ASSEMBLY LINE GP LOOP")
    
    current_gen = 0
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                current_gen = state.get("current_generation", 0)
        except Exception:
            pass

    for _ in range(gens):
        logging.info(f"--- Generation {current_gen} ---")
        log_aider(f"--- STARTING GENERATION {current_gen} ---")
        
        # Load the Vault
        vault = load_vault()
        log_aider(f"Vault loaded with {len(vault)} lineages")
        
        # Prepare the 6 slots
        next_population = []
        
        # SLOT 1: Mutated King (from Vault rank 1)
        if len(vault) > 0:
            king_source = copy.deepcopy(vault[0])
            # Ensure it has required fields
            if "lineage_id" not in king_source:
                king_source["lineage_id"] = str(uuid.uuid4())
            king = copy.deepcopy(king_source)
            # Apply micro-mutation
            apply_point_mutation(king["entry_tree"])
            apply_point_mutation(king["exit_tree"])
            king["status"] = "king"
            king["generation_age"] = king.get("generation_age", 0) + 1
            king["debuff_active_gens"] = 0
            king["fitness"] = -1.0  # Needs to be re-evaluated
            log_aider(f"Slot 1: Mutated King from lineage {king['lineage_id'][:8]}, Age incremented to {king['generation_age']}")
        else:
            # Fallback: generate alien outsider
            king = generate_ai_outsider("alien")
            king["status"] = "king"  # Override status for slot 1
            log_aider(f"Slot 1: Fallback to Alien Outsider (Vault empty)")
        next_population.append(king)
        
        # STEP A: Generate AI context
        try:
            generate_context_script = PROJECT_ROOT / "scripts" / "generate_ai_context.py"
            subprocess.run([sys.executable, str(generate_context_script)], 
                          capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
            log_aider("AI context generated successfully")
        except Exception as e:
            logging.warning(f"Failed to generate AI context: {e}")
        
        # STEP B: Strict retry loop for AI batch generation
        ai_batch_generator_script = PROJECT_ROOT / "scripts" / "ai_batch_generator.py"
        while True:
            try:
                result = subprocess.run(
                    [sys.executable, str(ai_batch_generator_script)],
                    capture_output=True,
                    text=True,
                    cwd=PROJECT_ROOT,
                    timeout=120
                )
                if result.returncode == 0:
                    log_aider("AI batch generated successfully")
                    break
                else:
                    logging.warning(f"AI batch generator failed with exit code {result.returncode}")
                    logging.warning(f"Stderr: {result.stderr[:200]}")
            except Exception as e:
                logging.warning(f"AI batch generator exception: {e}")
            
            print("⚠️ Gemini API Failed - Waiting 60 seconds before retrying...")
            log_aider("AI batch generation failed, waiting 60 seconds to retry")
            time.sleep(60)
        
        # STEP C: Load AI batch
        latest_batch_path = PROJECT_ROOT / "user_data" / "strategies" / "latest_ai_batch.json"
        try:
            with open(latest_batch_path, 'r') as f:
                ai_batch = json.load(f)
            log_aider(f"Loaded AI batch with {len(ai_batch)} strategies")
        except Exception as e:
            logging.error(f"Failed to load AI batch: {e}")
            sys.exit(1)
        
        # STEP D: Slot injection for slots 2-6
        # We need exactly 5 AI strategies for slots 2-6
        if len(ai_batch) != 5:
            logging.error(f"AI batch must contain exactly 5 strategies, got {len(ai_batch)}")
            sys.exit(1)
        
        for i, ai_strategy in enumerate(ai_batch):
            slot_num = i + 2  # Slots 2-6
            
            # Create a new individual based on AI strategy
            individual = {
                "entry_tree": ai_strategy.get("entry_tree"),
                "exit_tree": ai_strategy.get("exit_tree"),
                "fitness": -1.0,
                "generation_age": 0,
                "debuff_active_gens": 0,
                "status": None,  # Will be set based on type
                "lineage_id": None  # Will be set based on type
            }
            
            strategy_type = ai_strategy.get("type", "")
            
            # Handle different strategy types
            if strategy_type in ["mutated_rank_1", "mutated_rank_2"]:
                # These should preserve lineage from Vault
                rank_num = 1 if strategy_type == "mutated_rank_1" else 2
                rank_index = rank_num - 1  # Convert to 0-based index
                
                if len(vault) > rank_index:
                    # Use lineage from the corresponding vault entry
                    vault_entry = vault[rank_index]
                    individual["lineage_id"] = vault_entry.get("lineage_id", str(uuid.uuid4()))
                    individual["status"] = "candidate"
                    individual["debuff_active_gens"] = vault_entry.get("debuff_active_gens", 0) + 1
                    log_aider(f"Slot {slot_num}: AI {strategy_type} using lineage {individual['lineage_id'][:8]} from Vault rank {rank_num}")
                else:
                    # Fallback: generate new lineage
                    individual["lineage_id"] = str(uuid.uuid4())
                    individual["status"] = "candidate"
                    log_aider(f"Slot {slot_num}: AI {strategy_type} with new lineage (Vault insufficient)")
            
            elif strategy_type in ["guided_outsider", "alien_outsider_A", "alien_outsider_B"]:
                # These are outsiders - generate new lineage
                individual["lineage_id"] = str(uuid.uuid4())
                individual["status"] = "outsider"
                log_aider(f"Slot {slot_num}: AI {strategy_type} with new lineage {individual['lineage_id'][:8]}")
            
            else:
                # Unknown type - default to outsider
                individual["lineage_id"] = str(uuid.uuid4())
                individual["status"] = "outsider"
                log_aider(f"Slot {slot_num}: Unknown AI type '{strategy_type}', defaulting to outsider")
            
            next_population.append(individual)
        
        # Ensure we have exactly 6 individuals
        if len(next_population) != 6:
            logging.error(f"Population size mismatch: {len(next_population)} != 6")
            # Adjust by adding or removing as needed
            while len(next_population) < 6:
                next_population.append(generate_ai_outsider("alien"))
            next_population = next_population[:6]
        
        # Evaluate all individuals
        for i, ind in enumerate(next_population):
            if ind.get("fitness", -1.0) < 0:
                logging.info(f"Evaluating Individual {i+1}/6 ({ind.get('status', 'unknown')})...")
                fit = run_evolution_round(ind)
                ind["fitness"] = fit
                log_aider(f"Slot {i+1} ({ind['status']}) evaluated with fitness {fit:.4f}")
            else:
                logging.info(f"Skipping Individual {i+1}/6 ({ind.get('status', 'unknown')}) - already evaluated with fitness {ind['fitness']:.4f}")
        
        # Find the King (highest fitness) from evaluated population
        next_population.sort(key=lambda x: x.get("fitness", 0.0), reverse=True)
        best_individual = copy.deepcopy(next_population[0])
        
        # Update king status if necessary
        for ind in next_population:
            if ind.get("lineage_id") == best_individual.get("lineage_id"):
                ind["status"] = "king"
                ind["generation_age"] = ind.get("generation_age", 0) + 1
                ind["debuff_active_gens"] = 0
                best_individual = copy.deepcopy(ind)
                break
        
        # Get king's age for debuff calculations
        king_age = best_individual.get("generation_age", 0)
        
        # Calculate debuffed fitness for all individuals
        for ind in next_population:
            ind["debuffed_fitness"] = calculate_debuffed_fitness(ind, king_age)
        
        # Find maximum fitness among outsiders
        outsiders = [ind for ind in next_population if ind.get("status") == "outsider"]
        outsiders_max_fitness = max([ind.get("fitness", 0.0) for ind in outsiders]) if outsiders else 0.0
        
        # Check retirement for candidates and mutants
        for ind in next_population:
            check_retirement(ind, outsiders_max_fitness)
        
        # Save best individual to Vault
        save_to_vault(best_individual)
        logging.info(f"KING FITNESS: {best_individual['fitness']:.4f} | Lineage: {best_individual['lineage_id'][:8]} | Age: {king_age}")
        
        # Save population for next generation
        with open(POPULATION_FILE, 'w') as f:
            json.dump({"individuals": next_population}, f, indent=2)
        
        # Save generation state
        current_gen += 1
        with open(STATE_FILE, 'w') as f:
            json.dump({"current_generation": current_gen}, f, indent=2)
        
        # Sync with git
        try:
            subprocess.run(["bash", str(PROJECT_ROOT / "scripts" / "auto_sync.sh")], cwd=PROJECT_ROOT)
        except Exception as e:
            logging.warning(f"Git Sync Failed: {e}")

if __name__ == "__main__":
    run_loop(gens=1)
