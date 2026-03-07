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
CURRENT_GENOME_FILE = PROJECT_ROOT / "user_data" / "current_genome.json"
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
    """Save king to vault with ruthless pruning logic."""
    vault = []
    if VAULT_FILE.exists():
        try:
            with open(VAULT_FILE, 'r') as f:
                vault = json.load(f)
        except Exception:
            pass
    
    # Find existing entry with same lineage_id
    existing_index = -1
    for i, v in enumerate(vault):
        if v.get("lineage_id") == king.get("lineage_id"):
            existing_index = i
            break
    
    # Ruthless DNA Pruning: Winner Stays logic
    if existing_index >= 0:
        existing_fitness = vault[existing_index].get("fitness", 0.0)
        new_fitness = king.get("fitness", 0.0)
        
        if new_fitness > existing_fitness:
            # Overwrite existing entry
            vault[existing_index] = copy.deepcopy(king)
            logging.info(f"  > VAULT UPDATED (Lineage improved: {new_fitness:.4f} > {existing_fitness:.4f})")
        else:
            # Already in vault with better fitness
            return
    else:
        # New lineage: add to vault
        vault.append(copy.deepcopy(king))
    
    # Sort by fitness in descending order
    vault.sort(key=lambda x: x.get("fitness", 0.0), reverse=True)
    
    # Enforce hard cap of 30 entries
    if len(vault) > 30:
        vault = vault[:30]
    
    # Save vault
    VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(VAULT_FILE, 'w') as f:
        json.dump(vault, f, indent=2)
    
    # Perform periodic scrubbing of genomes directory
    scrub_genomes_directory(vault)
    
    logging.info(f"  > VAULT UPDATED. Top fitness: {vault[0].get('fitness', 0.0):.4f} | Total entries: {len(vault)}/30")

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
    # Use 5 Fixed Regimes (Expanded Coverage)
    periods = [
        "20260201-20260301", # Recent Market (1 month)
        "20241001-20241231", # Bull Market (3 months - High Priority)
        "20250101-20250301", # Bear Market (2 months - High Priority)
        "20240715-20240815", # Crash Market (1 month)
        "20240815-20241001"  # Sideways/Consolidation (1.5 months)
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
            genome["is_retired"] = True
            logging.info(f"  > Lineage {genome.get('lineage_id', 'unknown')[:8]} RETIRED due to low debuffed fitness.")

def generate_ai_outsider(type: str) -> Dict[str, Any]:
    """Generate a fresh random genome for AI outsiders."""
    # Generate fresh individual
    individual = create_fresh_individual("outsider")
    log_aider(f"Generated {type} outsider with lineage {individual['lineage_id'][:8]}")
    return individual

def load_vault() -> List[Dict[str, Any]]:
    """Load and sort the Vault (hall_of_fame.json)."""
    vault = []
    if VAULT_FILE.exists():
        try:
            with open(VAULT_FILE, 'r') as f:
                vault = json.load(f)
            
            # Upgrade legacy vault entries
            upgraded = False
            for entry in vault:
                if "lineage_id" not in entry:
                    entry["lineage_id"] = str(uuid.uuid4())
                    entry["generation_age"] = 0
                    entry["status"] = "king"
                    upgraded = True
            
            if upgraded:
                with open(VAULT_FILE, 'w') as f:
                    json.dump(vault, f, indent=2)
                logging.info("Upgraded legacy vault entries with lineage IDs.")

            # Sort by fitness in descending order
            vault.sort(key=lambda x: x.get("fitness", 0.0), reverse=True)
        except Exception as e:
            logging.error(f"Failed to load Vault: {e}")
    return vault

def scrub_genomes_directory(active_vault: List[Dict[str, Any]]):
    """Delete genome files that are not associated with active lineages."""
    if not GENOME_DIR.exists():
        return
    
    # Collect lineage_id prefixes (first 8 chars) from active vault
    active_prefixes = set()
    for entry in active_vault:
        lineage_id = entry.get("lineage_id")
        if lineage_id and len(lineage_id) >= 8:
            active_prefixes.add(lineage_id[:8])
    
    # Also check current population
    if POPULATION_FILE.exists():
        try:
            with open(POPULATION_FILE, 'r') as f:
                population_data = json.load(f)
                individuals = population_data.get("individuals", [])
                for ind in individuals:
                    lineage_id = ind.get("lineage_id")
                    if lineage_id and len(lineage_id) >= 8:
                        active_prefixes.add(lineage_id[:8])
        except Exception as e:
            logging.warning(f"Failed to load population for scrubbing: {e}")
    
    # Scrub all gen_*.json files
    for genome_file in GENOME_DIR.glob("gen_*.json"):
        if genome_file.name == "hall_of_fame.json":
            continue
        
        stem = genome_file.stem  # e.g., "gen_62c735f9" or "gen_343_king"
        
        # Determine if it's a lineage file or a legacy generation file
        # Format is gen_XXXXXXXX.json or gen_N_king.json
        match = re.match(r"^gen_([0-9a-f]{8})$", stem)
        if match:
            prefix = match.group(1)
            if prefix not in active_prefixes:
                try:
                    genome_file.unlink()
                    logging.info(f"  > RUTHLESS SCRUBBING: Deleted orphaned genome {genome_file.name}")
                except Exception as e:
                    logging.warning(f"Failed to delete {genome_file}: {e}")
        else:
            # It's a legacy gen_XXX_king.json or gen_XXX_best.json
            try:
                genome_file.unlink()
                logging.info(f"  > RUTHLESS SCRUBBING: Deleted legacy file {genome_file.name}")
            except Exception as e:
                logging.warning(f"Failed to delete legacy file {genome_file}: {e}")

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
        for i, ai_strategy in enumerate(ai_batch):
            slot_num = i + 2  # Slots 2-6
            individual = {
                "entry_tree": ai_strategy.get("entry_tree"),
                "exit_tree": ai_strategy.get("exit_tree"),
                "fitness": -1.0,
                "generation_age": 0,
                "debuff_active_gens": 0,
                "status": None,
                "lineage_id": None
            }
            
            strategy_type = ai_strategy.get("type", "")
            if strategy_type in ["mutated_rank_1", "mutated_rank_2"]:
                rank_num = 1 if strategy_type == "mutated_rank_1" else 2
                rank_index = rank_num - 1
                if len(vault) > rank_index:
                    vault_entry = vault[rank_index]
                    individual["lineage_id"] = vault_entry.get("lineage_id", str(uuid.uuid4()))
                    individual["status"] = "candidate"
                    individual["debuff_active_gens"] = vault_entry.get("debuff_active_gens", 0) + 1
                    log_aider(f"Slot {slot_num}: AI {strategy_type} using lineage {individual['lineage_id'][:8]}")
                else:
                    individual["lineage_id"] = str(uuid.uuid4())
                    individual["status"] = "candidate"
                    log_aider(f"Slot {slot_num}: AI {strategy_type} with new lineage")
            elif strategy_type in ["guided_outsider", "alien_outsider_A", "alien_outsider_B"]:
                individual["lineage_id"] = str(uuid.uuid4())
                individual["status"] = "outsider"
                log_aider(f"Slot {slot_num}: AI {strategy_type} with new lineage {individual['lineage_id'][:8]}")
            else:
                individual["lineage_id"] = str(uuid.uuid4())
                individual["status"] = "outsider"
                log_aider(f"Slot {slot_num}: Unknown AI type defaulting to outsider")
            next_population.append(individual)
        
        # Evaluate with smoke test pre-filter
        for i, ind in enumerate(next_population):
            if ind.get("fitness", -1.0) < 0:
                logging.info(f"Evaluating Individual {i+1}/6 ({ind.get('status', 'unknown')})...")
                
                # Run smoke test first
                smoke_test_script = PROJECT_ROOT / "scripts" / "smoke_test.py"
                if smoke_test_script.exists():
                    # Save the individual to a temporary file for smoke testing
                    temp_genome_path = GENOME_DIR / f"temp_smoke_{i}.json"
                    try:
                        with open(temp_genome_path, 'w') as f:
                            json.dump(ind, f, indent=2)
                        
                        # Run smoke test
                        result = subprocess.run(
                            [sys.executable, str(smoke_test_script), str(temp_genome_path)],
                            capture_output=True,
                            text=True,
                            timeout=15  # Should be less than 10 seconds, but give some buffer
                        )
                        
                        # Check result
                        if result.returncode == 0:
                            logging.info(f"  ✅ Slot {i+1} passed smoke test")
                            log_aider(f"Slot {i+1} passed smoke test")
                        else:
                            logging.info(f"  ❌ Slot {i+1} failed smoke test. Discarding.")
                            log_aider(f"Slot {i+1} failed smoke test")
                            ind["fitness"] = 0.0
                            # Clean up temp file
                            if temp_genome_path.exists():
                                temp_genome_path.unlink()
                            continue
                    except subprocess.TimeoutExpired:
                        logging.warning(f"  ⚠️ Slot {i+1} smoke test timed out. Treating as failed.")
                        log_aider(f"Slot {i+1} smoke test timed out")
                        ind["fitness"] = 0.0
                        continue
                    except Exception as e:
                        logging.error(f"  ⚠️ Smoke test error for slot {i+1}: {e}. Treating as failed.")
                        log_aider(f"Slot {i+1} smoke test error: {e}")
                        ind["fitness"] = 0.0
                        continue
                    finally:
                        # Clean up temp file if it exists
                        if temp_genome_path.exists():
                            try:
                                temp_genome_path.unlink()
                            except:
                                pass
                else:
                    logging.warning("Smoke test script not found, skipping smoke test")
                
                # If smoke test passed, run full evaluation
                if ind.get("fitness", -1.0) < 0:
                    fit = run_evolution_round(ind)
                    ind["fitness"] = fit
                    
                    # Save only if it's potentially active DNA
                    if fit > 0:
                        lineage_id = ind.get("lineage_id")
                        prefix = lineage_id[:8]
                        genome_file = GENOME_DIR / f"gen_{prefix}.json"
                        with open(genome_file, 'w') as f:
                            json.dump(ind, f, indent=2)
                    log_aider(f"Slot {i+1} ({ind['status']}) evaluated with fitness {fit:.4f}")
        
        # Update King
        next_population.sort(key=lambda x: x.get("fitness", 0.0), reverse=True)
        best_individual = copy.deepcopy(next_population[0])
        king_age = best_individual.get("generation_age", 0)
        
        # Calculate debuffs & Check retirement
        for ind in next_population:
            ind["debuffed_fitness"] = calculate_debuffed_fitness(ind, king_age)
        
        outsiders = [ind for ind in next_population if ind.get("status") == "outsider"]
        outsiders_max_fitness = max([ind.get("fitness", 0.0) for ind in outsiders]) if outsiders else 0.0
        
        for ind in next_population:
            check_retirement(ind, outsiders_max_fitness)
        
        # VAULT PERSISTENCE
        if best_individual["fitness"] > 0:
            save_to_vault(best_individual)
        
        # Always scrub orphaned/legacy genomes
        scrub_genomes_directory(load_vault())
        
        # Save population
        with open(POPULATION_FILE, 'w') as f:
            json.dump({"individuals": next_population}, f, indent=2)
        
        current_gen += 1
        with open(STATE_FILE, 'w') as f:
            json.dump({"current_generation": current_gen}, f, indent=2)
        
        # Commit the changes if this is the first generation with smoke test
        if current_gen == 0:
            try:
                subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, capture_output=True, text=True)
                subprocess.run(["git", "commit", "-m", "Engine V2.6: Implemented Flash-Test Gatekeeper"], 
                             cwd=PROJECT_ROOT, capture_output=True, text=True)
                logging.info("✅ Committed smoke test implementation")
            except Exception as e:
                logging.warning(f"Git commit failed: {e}")
        
        try:
            subprocess.run(["bash", str(PROJECT_ROOT / "scripts" / "auto_sync.sh")], cwd=PROJECT_ROOT)
        except Exception as e:
            logging.warning(f"Git Sync Failed: {e}")

if __name__ == "__main__":
    run_loop(gens=1)
