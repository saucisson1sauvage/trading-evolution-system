import random
import json
import os
import copy
import logging
import subprocess
import re
import math
import datetime
from typing import Dict, Any, List, Tuple
from pathlib import Path
import sys

# Paths
PROJECT_ROOT = Path("/home/saus/crypto-crew-4.0")
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

# Grammar Definitions
BOOL_PRIMITIVES = ["GREATER_THAN", "LESS_THAN", "CROSS_UP", "CROSS_DOWN"]
BOOL_OPERATORS = ["AND", "OR", "NOT"]
BOOL_HELPERS = ["TRENDING_UP", "TRENDING_DOWN", "VOLATILE", "VOLUME_SPIKE"]
NUM_INDICATORS = ["RSI", "EMA", "SMA", "BB_UPPER", "BB_MIDDLE", "BB_LOWER"]

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
    raw_str = json.dumps({"entry": genome["entry_tree"], "exit": genome["exit_tree"]})
    return re.sub(r'(\d+\.\d+)', lambda m: str(round(float(m.group(1)))), raw_str)

def save_to_vault(king: dict):
    vault = []
    if VAULT_FILE.exists():
        try:
            with open(VAULT_FILE, 'r') as f:
                vault = json.load(f)
        except Exception:
            pass
    
    king_hash = get_similarity_hash(king)
    for i, v in enumerate(vault):
        v_hash = get_similarity_hash(v)
        if v_hash == king_hash:
            if king.get("fitness", 0.0) > v.get("fitness", 0.0):
                vault[i] = copy.deepcopy(king)
                vault.sort(key=lambda x: x.get("fitness", 0.0), reverse=True)
                with open(VAULT_FILE, 'w') as f:
                    json.dump(vault, f, indent=2)
                logging.info(f"  > VAULT UPDATED (Overwrote clone). Top fitness: {vault[0].get('fitness', 0.0):.4f}")
            return

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
    
    command = [
        "/home/saus/freqtrade/.venv/bin/freqtrade", "backtesting",
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

def run_loop(gens=50):
    logging.info(f"STARTING 6-SLOT ROLE-BASED GP LOOP")
    
    current_gen = 0
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                current_gen = state.get("current_generation", 0)
        except Exception:
            pass

    population = []
    if POPULATION_FILE.exists():
        try:
            with open(POPULATION_FILE, 'r') as f:
                data = json.load(f)
                population = data.get("individuals", [])
                # Reset fitness if transitioning from old engine (individuals missing 'role')
                if population and "role" not in population[0]:
                    logging.info("Old population format detected. Resetting fitness for recalibration.")
                    for ind in population:
                        ind["fitness"] = -1.0
        except Exception as e:
            logging.error(f"Failed to load population: {e}")

    while len(population) < 6:
        population.append({
            "entry_tree": generate_bool_node(0, 3),
            "exit_tree": generate_bool_node(0, 3),
            "fitness": -1.0,
            "generation_age": 0,
            "role": "outsider"
        })
    population = population[:6]

    for _ in range(gens):
        logging.info(f"--- Generation {current_gen} ---")
        log_aider(f"--- STARTING GENERATION {current_gen} ---")
        # Evaluate
        for i, ind in enumerate(population):
            if ind.get("fitness", -1.0) < 0:
                logging.info(f"Evaluating Individual {i+1}/6 ({ind.get('role', 'unknown')})...")
                fit = run_evolution_round(ind)
                ind["fitness"] = fit
            else:
                logging.info(f"Skipping Individual {i+1}/6 ({ind.get('role', 'unknown')}) - already evaluated with fitness {ind['fitness']:.4f}")
                
        for ind in population:
            age = ind.get("generation_age", 0)
            if ind.get("role") == "king":
                ind["debuffed_fitness"] = ind["fitness"]
            else:
                ind["debuffed_fitness"] = ind["fitness"] * (0.85 ** age)

        population.sort(key=lambda x: x.get("fitness", 0.0), reverse=True)
        king = copy.deepcopy(population[0])
        king["role"] = "king"
        king["generation_age"] = 0
        king["debuffed_fitness"] = king["fitness"]
        
        logging.info(f"KING FITNESS: {king['fitness']:.4f}")
        log_aider(f"Best raw fitness found in Gen {current_gen}: {king['fitness']:.4f}")
        save_to_vault(king)

        remaining = population[1:]
        remaining.sort(key=lambda x: x.get("debuffed_fitness", 0.0), reverse=True)
        cand1_source = remaining[0]
        cand2_source = remaining[1]

        next_population = []
        next_population.append(copy.deepcopy(king))
        
        c1 = copy.deepcopy(cand1_source)
        apply_point_mutation(c1["entry_tree"])
        apply_point_mutation(c1["exit_tree"])
        c1["role"] = "candidate"
        c1["generation_age"] = c1.get("generation_age", 0) + 1
        c1["fitness"] = -1.0
        next_population.append(c1)

        c2 = copy.deepcopy(cand2_source)
        apply_point_mutation(c2["entry_tree"])
        apply_point_mutation(c2["exit_tree"])
        c2["role"] = "candidate"
        c2["generation_age"] = c2.get("generation_age", 0) + 1
        c2["fitness"] = -1.0
        next_population.append(c2)

        mut = copy.deepcopy(king)
        apply_structural_mutation(mut["entry_tree"])
        apply_structural_mutation(mut["exit_tree"])
        mut["role"] = "mutant"
        mut["generation_age"] = 0
        mut["fitness"] = -1.0
        next_population.append(mut)

        out1 = {
            "entry_tree": generate_bool_node(0, 3),
            "exit_tree": generate_bool_node(0, 3),
            "role": "outsider",
            "generation_age": 0,
            "fitness": -1.0
        }
        out2 = {
            "entry_tree": generate_bool_node(0, 3),
            "exit_tree": generate_bool_node(0, 3),
            "role": "outsider",
            "generation_age": 0,
            "fitness": -1.0
        }
        next_population.extend([out1, out2])

        GENOME_DIR.mkdir(parents=True, exist_ok=True)
        with open(GENOME_DIR / f"gen_{current_gen}_king.json", 'w') as f:
            json.dump(king, f, indent=2)

        with open(POPULATION_FILE, 'w') as f:
            json.dump({"individuals": next_population}, f, indent=2)

        current_gen += 1
        with open(STATE_FILE, 'w') as f:
            json.dump({"current_generation": current_gen}, f, indent=2)
            
        population = next_population

        try:
            subprocess.run(["bash", str(PROJECT_ROOT / "scripts" / "auto_sync.sh")], cwd=PROJECT_ROOT)
        except Exception as e:
            logging.warning(f"Git Sync Failed: {e}")

if __name__ == "__main__":
    run_loop(gens=1)
