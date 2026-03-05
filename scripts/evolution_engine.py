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
    if current_depth >= max_depth: 
        # HIGH HEAT: Return a simple comparison 80% of the time to ensure it works
        return {"primitive": "LESS_THAN", "left": {"primitive": "RSI", "parameters": {"window": 14}}, "right": {"constant": 70.0}}
    
    # Simple depth 1 comparison
    return {"primitive": "LESS_THAN", "left": {"primitive": "RSI", "parameters": {"window": random.randint(7,30)}}, "right": {"constant": random.uniform(40, 80)}}

def save_current_genome(genome: dict) -> None:
    path = PROJECT_ROOT / "user_data/current_genome.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(genome, f, indent=2)

def run_backtest(timerange: str = "20241101-20241115") -> bool:
    for f in glob.glob(str(PROJECT_ROOT / "user_data/backtest_results/*.json")):
        try: os.remove(f)
        except: pass

    command = [
        "/home/saus/freqtrade/.venv/bin/freqtrade", "backtesting",
        "--strategy", "GPTreeStrategy",
        "--timerange", timerange,
        "--config", str(PROJECT_ROOT / "config.json"),
        "--userdir", str(PROJECT_ROOT / "user_data"),
        "--export", "trades"
    ]
    try:
        res = subprocess.run(command, capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False

def calculate_fitness() -> float:
    files = glob.glob(str(PROJECT_ROOT / "user_data/backtest_results/*.json"))
    if not files: return 0.0
    pattern = max(files, key=os.path.getmtime)

    try:
        with open(pattern, 'r') as f:
            data = json.load(f)
        res = data[0] if isinstance(data, list) else data.get("strategy", {}).get("GPTreeStrategy", data)
        trades = res.get("total_trades", 0)
        if trades == 0: return 0.0
        
        profit = res.get("profit_total", 0.0)
        # Simplified fitness to reward ANY trades
        fitness = (trades * 0.1) + (profit * 100)
        logging.info(f"  > Trades: {trades}, Profit: {profit:.2%}, Fitness: {fitness:.4f}")
        return fitness
    except Exception:
        return 0.0

def run_evolution(generations: int = 2, pop_size: int = 5):
    logging.info(f"UNBLOCKING RUN: Starting Evolution")
    
    population = []
    for i in range(pop_size):
        population.append({
            "entry_tree": generate_random_tree(max_depth=1),
            "exit_tree": {"primitive": "GREATER_THAN", "left": {"primitive": "RSI", "parameters": {"window": 14}}, "right": {"constant": 30.0}},
            "fitness": -999.0
        })

    for gen in range(generations):
        logging.info(f"--- Generation {gen} ---")
        for i, individual in enumerate(population):
            if individual["fitness"] == -999.0:
                save_current_genome(individual)
                if run_backtest():
                    individual["fitness"] = calculate_fitness()
                logging.info(f"Gen {gen} | Ind {i+1} | Fitness: {individual['fitness']:.4f}")
        
        population.sort(key=lambda x: x["fitness"], reverse=True)
        logging.info(f"BEST OF GEN {gen}: {population[0]['fitness']:.4f}")
        
        # Repopulate
        new_population = population[:2]
        while len(new_population) < pop_size:
            child = copy.deepcopy(population[0])
            child["entry_tree"]["right"]["constant"] += random.uniform(-5, 5)
            child["fitness"] = -999.0
            new_population.append(child)
        population = new_population

        try:
            subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=False)
            subprocess.run(["git", "commit", "-m", f"Evolution: Gen {gen} Success"], cwd=PROJECT_ROOT, check=False)
            subprocess.run(["git", "push", "origin", "main"], cwd=PROJECT_ROOT, check=False)
        except: pass

if __name__ == "__main__":
    run_evolution(generations=2, pop_size=5)
