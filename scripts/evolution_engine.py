import random
import json
import os
import copy
import logging
import glob
import subprocess
import time
import sys
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

# Paths
PROJECT_ROOT = Path("/home/saus/crypto-crew-4.0")
STRATEGY_DIR = PROJECT_ROOT / "user_data/strategies"
GENOME_DIR = STRATEGY_DIR / "genomes"
POPULATION_FILE = STRATEGY_DIR / "population.json"
STATE_FILE = STRATEGY_DIR / "state.json"
CURRENT_GENOME_FILE = PROJECT_ROOT / "user_data/current_genome.json"
LOG_FILE = PROJECT_ROOT / "user_data/logs/evolution.log"

sys.path.append(str(PROJECT_ROOT))

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
    # Randomly choose between indicator and constant
    if depth >= max_depth or random.random() < 0.3:
        if random.random() < 0.7:
             name = random.choice(NUM_INDICATORS)
             params = {"window": random.randint(7, 50)}
             if "BB" in name:
                 params["std"] = round(random.uniform(1.5, 3.0), 1)
             return {"primitive": name, "parameters": params}
        else:
             # LOOSENED CONSTANTS: Start with more plausible values (20-80 instead of 10-90)
             return {"constant": round(random.uniform(20, 80), 2)}
    
    # Numeric nodes are currently leaf-like (Indicators or Constants)
    name = random.choice(NUM_INDICATORS)
    params = {"window": random.randint(7, 50)}
    if "BB" in name:
        params["std"] = round(random.uniform(1.5, 3.0), 1)
    return {"primitive": name, "parameters": params}

def generate_bool_node(depth: int, max_depth: int) -> Dict[str, Any]:
    if depth < max_depth and random.random() < 0.5:
        # Operator
        op = random.choice(BOOL_OPERATORS)
        if op == "NOT":
            return {"operator": "NOT", "children": [generate_bool_node(depth + 1, max_depth)]}
        else:
            return {"operator": op, "children": [generate_bool_node(depth + 1, max_depth), generate_bool_node(depth + 1, max_depth)]}
    elif random.random() < 0.4:
        # Boolean Helpers (TRENDING_UP, etc.)
        name = random.choice(BOOL_HELPERS)
        params = {"window": random.randint(7, 50)}
        if name == "VOLATILE":
             params["threshold"] = round(random.uniform(1.1, 2.5), 2)
        return {"primitive": name, "parameters": params}
    else:
        # Comparator
        return {
            "primitive": random.choice(BOOL_PRIMITIVES),
            "left": generate_num_node(depth + 1, max_depth),
            "right": generate_num_node(depth + 1, max_depth)
        }

def get_all_nodes(node: Dict[str, Any], node_type: str) -> List[Dict[str, Any]]:
    """Returns a list of references to sub-nodes of a certain type."""
    nodes = []
    
    # Determine type of current node
    current_type = None
    if "operator" in node or ("primitive" in node and (node["primitive"] in BOOL_PRIMITIVES or node["primitive"] in BOOL_HELPERS)):
        current_type = "bool"
    elif "constant" in node or ("primitive" in node and node["primitive"] in NUM_INDICATORS):
        current_type = "num"
        
    if current_type == node_type:
        nodes.append(node)
        
    # Recurse
    if "children" in node:
        for child in node["children"]:
            nodes.extend(get_all_nodes(child, node_type))
    if "left" in node:
        nodes.extend(get_all_nodes(node["left"], node_type))
    if "right" in node:
        nodes.extend(get_all_nodes(node["right"], node_type))
        
    return nodes

def crossover_tree(t1: Dict[str, Any], t2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    c1, c2 = copy.deepcopy(t1), copy.deepcopy(t2)
    
    # Randomly pick between bool and num nodes for crossover
    types = ["bool", "num"]
    random.shuffle(types)
    
    for t in types:
        n1 = get_all_nodes(c1, t)
        n2 = get_all_nodes(c2, t)
        if n1 and n2:
            target1 = random.choice(n1)
            target2 = random.choice(n2)
            # Swap contents
            tmp = copy.deepcopy(target1)
            target1.clear()
            target1.update(target2)
            target2.clear()
            target2.update(tmp)
            return c1, c2
    return c1, c2

def mutate_tree(tree: Dict[str, Any], max_depth: int):
    # Point mutation vs Subtree mutation
    if random.random() < 0.6:
        # Point Mutation
        types = ["bool", "num"]
        random.shuffle(types)
        for t in types:
            nodes = get_all_nodes(tree, t)
            if nodes:
                target = random.choice(nodes)
                if "constant" in target:
                    target["constant"] = round(max(0, min(100, target["constant"] + random.uniform(-10, 10))), 2)
                elif "parameters" in target:
                    target["parameters"]["window"] = max(5, min(100, target["parameters"]["window"] + random.randint(-5, 5)))
                    if "std" in target["parameters"]:
                        target["parameters"]["std"] = round(max(1.0, min(4.0, target["parameters"]["std"] + random.uniform(-0.2, 0.2))), 1)
                elif "primitive" in target:
                    if target["primitive"] in BOOL_PRIMITIVES:
                        target["primitive"] = random.choice(BOOL_PRIMITIVES)
                    elif target["primitive"] in BOOL_HELPERS:
                        target["primitive"] = random.choice(BOOL_HELPERS)
                    else:
                        target["primitive"] = random.choice(NUM_INDICATORS)
                        if "BB" in target["primitive"] and "std" not in target["parameters"]:
                             target["parameters"]["std"] = 2.0
                elif "operator" in target:
                    target["operator"] = random.choice(BOOL_OPERATORS)
                    # Handle child count if operator changed to/from NOT
                    if target["operator"] == "NOT" and len(target["children"]) > 1:
                        target["children"] = [target["children"][0]]
                    elif target["operator"] != "NOT" and len(target["children"]) == 1:
                        target["children"].append(generate_bool_node(0, 1))
                break
    else:
        # Subtree Mutation
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

def run_evolution_round(genome: dict) -> float:
    # Ensure directory exists
    CURRENT_GENOME_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CURRENT_GENOME_FILE, 'w') as f:
        json.dump(genome, f, indent=2)
    
    command = [
        "/home/saus/freqtrade/.venv/bin/freqtrade", "backtesting",
        "--strategy", "GPTreeStrategy",
        "--timerange", "20241101-20241115",
        "--config", str(PROJECT_ROOT / "config.json"),
        "--userdir", str(PROJECT_ROOT / "user_data"),
        "--cache", "none"
    ]
    try:
        logging.info(f"  > Launching Freqtrade Backtest...")
        res = subprocess.run(command, capture_output=True, text=True, timeout=60)
        output = res.stdout
        
        # Log Freqtrade output
        with open(PROJECT_ROOT / "user_data/logs/freqtrade_runs.log", "a") as flog:
            flog.write(f"\n--- NEW RUN ---\n{output}\n")
        
        # Print the cool table for the user
        strat_summary_idx = output.find("STRATEGY SUMMARY")
        if strat_summary_idx != -1:
            print("\n" + output[strat_summary_idx:].strip() + "\n")
        
        # Regex parsing for multiple metrics (handling both | and │)
        profit_pct = 0.0
        trades = 0
        sharpe = -5.0
        drawdown = 100.0
        
        # 1. Strategy Summary Table (Profit & Trades)
        sum_match = re.search(r"GPTreeStrategy\s+[|│]\s+(\d+)\s+[|│]\s+([\d\.-]+)\s+[|│]\s+([\d\.-]+)\s+[|│]\s+([\d\.-]+)", output)
        if sum_match:
            trades = int(sum_match.group(1))
            profit_pct = float(sum_match.group(4))
            
        # 2. Sharpe Ratio (Summary Metrics)
        sharpe_match = re.search(r"Sharpe\s+[|│]\s+([\d\.-]+)", output)
        if sharpe_match:
            sharpe = float(sharpe_match.group(1))
            
        # 3. Drawdown % (Summary Metrics)
        dd_match = re.search(r"Absolute drawdown\s+[|│]\s+[\d\.-]+\s+USDT\s+\(([\d\.-]+)%\)", output)
        if dd_match:
            drawdown = float(dd_match.group(1))
            
        if trades > 0:
            # TUNE FITNESS: Profit + (Sharpe * 0.5) - (Drawdown * 0.1)
            # If no trades or very low, penalize
            if trades < 5:
                fitness = profit_pct * 0.1
            else:
                fitness = profit_pct + (max(0, sharpe) * 0.5) - (drawdown * 0.1)
                
            logging.info(f"  > SUCCESS: Trades: {trades}, Profit: {profit_pct}%, Sharpe: {sharpe}, DD: {drawdown}% -> Fitness: {fitness:.4f}")
            
            # REWARD TRACKING: If AI fixed this and it made profit, log it for future LLM context
            if genome.get("ai_fixed") and profit_pct > 0:
                with open(PROJECT_ROOT / "user_data/logs/ai_success_hall_of_fame.log", "a") as f:
                    f.write(json.dumps({"fitness": fitness, "profit": profit_pct, "genome": genome}) + "\n")
            
            return fitness
        
        logging.warning("  > No trades found or parsing failed.")
        return 0.0
    except subprocess.TimeoutExpired:
        logging.error("  > Backtest timed out.")
        return 0.0
    except Exception as e:
        logging.error(f"  > Exec Error: {e}")
        return 0.0

def run_loop(gens=50, pop_size=20):
    logging.info(f"STARTING GP LOOP: {gens} gens, {pop_size} individuals")
    
    # Load generation state
    current_gen = 0
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                current_gen = state.get("current_generation", 0)
        except Exception:
            pass

    # Load population
    population = []
    if POPULATION_FILE.exists():
        try:
            with open(POPULATION_FILE, 'r') as f:
                data = json.load(f)
                population = data.get("individuals", [])
                logging.info(f"Loaded {len(population)} individuals from persistence.")
        except Exception as e:
            logging.error(f"Failed to load population: {e}")

    # Initialize missing
    while len(population) < pop_size:
        population.append({
            "entry_tree": generate_bool_node(0, 3),
            "exit_tree": generate_bool_node(0, 3),
            "fitness": -1.0
        })

    for _ in range(gens):
        logging.info(f"--- Generation {current_gen} ---")
        
        # Evaluate
        for i, ind in enumerate(population):
            if ind.get("fitness", -1.0) < 0:
                logging.info(f"Evaluating Individual {i+1}/{pop_size}...")
                ind["fitness"] = run_evolution_round(ind)
        
        population.sort(key=lambda x: x.get("fitness", -999.0), reverse=True)
        best = population[0]
        logging.info(f"BEST FITNESS: {best.get('fitness', 0.0):.4f}")
        
        # Save best
        GENOME_DIR.mkdir(parents=True, exist_ok=True)
        with open(GENOME_DIR / f"gen_{current_gen}_best.json", 'w') as f:
            json.dump(best, f, indent=2)

        # Save population
        with open(POPULATION_FILE, 'w') as f:
            json.dump({"individuals": population}, f, indent=2)

        # Update state
        current_gen += 1
        with open(STATE_FILE, 'w') as f:
            json.dump({"current_generation": current_gen}, f, indent=2)

        # Selection & Reproduction
        new_population = population[:2] # Elitism (top 2)
        
        mutations_done = 0
        while len(new_population) < pop_size:
            r = random.random()
            if r < 0.7: # Crossover
                p1, p2 = random.sample(population[:max(5, len(population)//2)], 2)
                ce1, ce2 = crossover_tree(p1["entry_tree"], p2["entry_tree"])
                cx1, cx2 = crossover_tree(p1["exit_tree"], p2["exit_tree"])
                new_population.append({"entry_tree": ce1, "exit_tree": cx1, "fitness": -1.0})
                if len(new_population) < pop_size:
                    new_population.append({"entry_tree": ce2, "exit_tree": cx2, "fitness": -1.0})
            elif r < 0.9 and mutations_done < 5: # Mutation (Capped at 5)
                p = copy.deepcopy(random.choice(population[:max(5, len(population)//2)]))
                mutate_tree(p["entry_tree"], 3)
                mutate_tree(p["exit_tree"], 3)
                p["fitness"] = -1.0
                new_population.append(p)
                mutations_done += 1
            else: # Random New Blood
                new_population.append({
                    "entry_tree": generate_bool_node(0, 3),
                    "exit_tree": generate_bool_node(0, 3),
                    "fitness": -1.0
                })
        
        population = new_population[:pop_size]

        # Sync
        try:
            subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT)
            subprocess.run(["git", "commit", "-m", f"GP Gen {current_gen} | Fitness {best.get('fitness', 0.0):.4f}"], cwd=PROJECT_ROOT)
            subprocess.run(["git", "push", "origin", "main"], cwd=PROJECT_ROOT)
        except Exception as e:
            logging.warning(f"Git Sync Failed: {e}")

if __name__ == "__main__":
    run_loop()
