import random
import json
import os
import copy
import logging
import glob
import subprocess
import time
import sys
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path("/home/saus/crypto-crew-4.0")
sys.path.append(str(PROJECT_ROOT))

# Constants
OPERATORS = ["AND", "OR", "NOT"]
COMPARATORS = ["GREATER_THAN", "LESS_THAN", "CROSS_UP", "CROSS_DOWN"]
INDICATORS = ["RSI", "EMA", "SMA", "BB_UPPER", "BB_MIDDLE", "BB_LOWER"]

# Configure Logging
LOG_PATH = PROJECT_ROOT / "user_data/logs/evolution.log"
os.makedirs(LOG_PATH.parent, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, mode='a'),
        logging.StreamHandler()
    ]
)

def generate_random_tree(max_depth: int, current_depth: int = 0) -> Dict[str, Any]:
    if current_depth >= max_depth: return _generate_indicator_node()
    choice = random.random()
    
    # "High Temperature" Bias: Make trees simpler and more permissive initially
    # 40% chance of operator, 60% chance of comparator (leaf-ish)
    if choice < 0.4:
        # Bias towards OR to ensure signals fire
        op = "OR" if random.random() < 0.7 else random.choice(["AND", "NOT"])
        
        if op == "NOT":
            children = [generate_random_tree(max_depth, current_depth+1)]
        else:
            children = [
                generate_random_tree(max_depth, current_depth+1),
                generate_random_tree(max_depth, current_depth+1)
            ]
        return {"operator": op, "children": children}
    else:
        # Comparator
        comp = random.choice(COMPARATORS)
        left = _generate_indicator_node()
        # High probability of constant comparison (easier to hit)
        right = {"constant": round(random.uniform(20, 80), 2)} if random.random() < 0.6 else _generate_indicator_node()
        return {"primitive": comp, "left": left, "right": right}

def _generate_indicator_node() -> Dict[str, Any]:
    if random.random() < 0.3: return {"constant": round(random.uniform(10, 90), 2)}
    ind = random.choice(INDICATORS)
    params = {"window": random.randint(7, 50)}
    if "BB_" in ind: params["std"] = round(random.uniform(1.5, 3.0), 1)
    return {"primitive": ind, "parameters": params}

def save_current_genome(genome: dict) -> None:
    path = PROJECT_ROOT / "user_data/current_genome.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(genome, f, indent=2)

def run_backtest(timerange: str = "20241101-20241115") -> bool:
    # Cleanup previous results
    for f in glob.glob(str(PROJECT_ROOT / "user_data/backtest_results/*.json")):
        try: os.remove(f)
        except: pass

    command = [
        "/home/saus/freqtrade/.venv/bin/freqtrade", "backtesting",
        "--strategy", "GPTreeStrategy",
        "--timerange", timerange,
        "--config", str(PROJECT_ROOT / "config.json"),
        "--userdir", str(PROJECT_ROOT / "user_data"),
        "--export", "trades",
        "--notes", "evolution_run"
    ]
    try:
        res = subprocess.run(command, capture_output=True, text=True)
        if res.returncode != 0:
            logging.error(f"Freqtrade Error: {res.stderr}")
            return False
        return True
    except Exception as e:
        logging.error(f"System Error: {e}")
        return False

def calculate_fitness() -> float:
    # Find the most recent json result
    files = glob.glob(str(PROJECT_ROOT / "user_data/backtest_results/*.json"))
    if not files: return 0.0
    pattern = max(files, key=os.path.getmtime)

    try:
        with open(pattern, 'r') as f:
            data = json.load(f)
        
        res = data[0] if isinstance(data, list) else data.get("strategy", {}).get("GPTreeStrategy", data)
        if not res: return 0.0
        
        trades = res.get("total_trades", 0)
        if trades == 0: return 0.0
        
        profit = res.get("profit_total", 0.0)
        sharpe = res.get("sharpe", 0.0)
        drawdown = abs(res.get("max_drawdown_account", 0.0))
        
        # Fitness Function
        fitness = (profit * 100) + (sharpe * 10) - (drawdown * 100)
        if trades < 5: fitness *= 0.5
        
        logging.info(f"  > Trades: {trades}, Profit: {profit:.2%}, Sharpe: {sharpe:.2f} -> Fitness: {fitness:.4f}")
        return fitness
    except Exception as e:
        logging.error(f"Parsing error: {e}")
        return 0.0

def tournament_selection(population: List[Dict], tournament_size: int = 3) -> Dict:
    subset = random.sample(population, min(len(population), tournament_size))
    return max(subset, key=lambda x: x.get("fitness", -999.0))

def mutate_tree(tree: Dict[str, Any], mutation_rate: float = 0.2) -> Dict[str, Any]:
    # Replace the tree with a new random one 20% of the time (High Temp)
    if random.random() < mutation_rate:
        return generate_random_tree(max_depth=3)
    return tree

def run_evolution(generations: int = 50, pop_size: int = 10):
    logging.info(f"Starting Evolution: {generations} generations, Population: {pop_size}")
    
    # 1. Initialize Population
    population = []
    for i in range(pop_size):
        # Start with simpler trees (depth 2) to ensure trades happen
        genome = {
            "entry_tree": generate_random_tree(max_depth=2),
            "exit_tree": generate_random_tree(max_depth=2),
            "fitness": -999.0
        }
        population.append(genome)

    # Ensure genomes directory exists
    os.makedirs(PROJECT_ROOT / "user_data/strategies/genomes", exist_ok=True)

    for gen in range(generations):
        logging.info(f"--- Generation {gen} ---")
        
        # 2. Evaluate Fitness
        for i, individual in enumerate(population):
            if individual["fitness"] == -999.0:
                save_current_genome(individual)
                if run_backtest():
                    individual["fitness"] = calculate_fitness()
                else:
                    individual["fitness"] = -1000.0
                
                logging.info(f"Gen {gen} | Ind {i+1}/{pop_size} | Fitness: {individual['fitness']:.4f}")
        
        # Sort by fitness
        population.sort(key=lambda x: x["fitness"], reverse=True)
        best_fitness = population[0]["fitness"]
        logging.info(f"TOP FITNESS GEN {gen}: {best_fitness:.4f}")
        
        # Save best genome
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        history_path = PROJECT_ROOT / f"user_data/strategies/genomes/gen_{gen}_best_{best_fitness:.4f}.json"
        with open(history_path, 'w') as f:
            json.dump(population[0], f, indent=2)

        # 3. Create Next Generation
        new_population = population[:2]  # Keep top 2
        
        while len(new_population) < pop_size:
            parent = tournament_selection(population)
            child = copy.deepcopy(parent)
            child["entry_tree"] = mutate_tree(child["entry_tree"])
            child["exit_tree"] = mutate_tree(child["exit_tree"])
            child["fitness"] = -999.0
            new_population.append(child)
            
        population = new_population

        # 4. Auto-Commit Progress
        try:
            subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=False)
            subprocess.run(["git", "commit", "-m", f"Evolution: Gen {gen} Complete - Best Fitness {best_fitness:.4f}"], cwd=PROJECT_ROOT, check=False)
            subprocess.run(["git", "push", "origin", "main"], cwd=PROJECT_ROOT, check=False)
        except Exception as e:
            logging.warning(f"Git sync failed: {e}")

if __name__ == "__main__":
    run_evolution(generations=50, pop_size=10)
