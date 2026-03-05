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
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

PROJECT_ROOT = Path("/home/saus/crypto-crew-4.0")
sys.path.append(str(PROJECT_ROOT))

# Constants
OPERATORS = ["AND", "OR", "NOT"]
COMPARATORS = ["GREATER_THAN", "LESS_THAN", "CROSS_UP", "CROSS_DOWN"]
INDICATORS = ["RSI", "EMA", "SMA", "BB_UPPER", "BB_MIDDLE", "BB_LOWER"]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.FileHandler(PROJECT_ROOT / "user_data/logs/evolution.log", mode='a'), logging.StreamHandler()]
)

def generate_random_tree(max_depth: int) -> Dict[str, Any]:
    # Depth 1 only: Ensure high signal probability
    return {"primitive": "LESS_THAN", "left": {"primitive": "RSI", "parameters": {"window": random.randint(7,21)}}, "right": {"constant": random.uniform(50, 80)}}

def save_current_genome(genome: dict) -> None:
    with open(PROJECT_ROOT / "user_data/current_genome.json", 'w') as f:
        json.dump(genome, f, indent=2)

def run_evolution_round(genome: dict) -> float:
    save_current_genome(genome)
    command = [
        "/home/saus/freqtrade/.venv/bin/freqtrade", "backtesting",
        "--strategy", "GPTreeStrategy",
        "--timerange", "20241101-20241115",
        "--config", str(PROJECT_ROOT / "config.json"),
        "--userdir", str(PROJECT_ROOT / "user_data")
    ]
    try:
        res = subprocess.run(command, capture_output=True, text=True)
        output = res.stdout
        
        # REGEX PARSING: Look for the result in the console table
        # Matches: | GPTreeStrategy | 26 | 0.41 | 10.663 | 1.07 |
        match = re.search(r"GPTreeStrategy\s+\|\s+(\d+)\s+\|\s+([\d\.-]+)\s+\|\s+([\d\.-]+)\s+\|\s+([\d\.-]+)", output)
        if match:
            trades = int(match.group(1))
            profit_pct = float(match.group(4))
            fitness = (trades * 0.01) + profit_pct
            logging.info(f"  > SUCCESS: Trades: {trades}, Profit: {profit_pct}% -> Fitness: {fitness:.4f}")
            return fitness
        
        logging.warning("  > No trades or parsing failed.")
        return 0.0
    except Exception as e:
        logging.error(f"  > Exec Error: {e}")
        return 0.0

def run_loop(gens=5, pop=4):
    logging.info(f"STARTING GP LOOP: {gens} gens, {pop} individuals")
    # Dynamic initial population with randomized exit points
    population = []
    for _ in range(pop):
        ind = {
            "entry_tree": generate_random_tree(1), 
            "exit_tree": {"primitive": "GREATER_THAN", "left": {"primitive": "RSI", "parameters": {"window": 14}}, "right": {"constant": random.uniform(70, 95)}},
            "fitness": -1.0
        }
        population.append(ind)

    for g in range(gens):
        logging.info(f"Gen {g}")
        for ind in population:
            if ind["fitness"] < 0:
                ind["fitness"] = run_evolution_round(ind)
        
        population.sort(key=lambda x: x["fitness"], reverse=True)
        best = population[0]
        logging.info(f"BEST FITNESS: {best['fitness']:.4f}")
        
        # Save best
        with open(PROJECT_ROOT / f"user_data/strategies/genomes/gen_{g}_best.json", 'w') as f:
            json.dump(best, f, indent=2)

        # Repopulate (Mutation only for stability)
        new_pop = [copy.deepcopy(best), copy.deepcopy(best)]
        while len(new_pop) < pop:
            child = copy.deepcopy(best)
            child["entry_tree"]["right"]["constant"] += random.uniform(-5, 5)
            child["fitness"] = -1.0
            new_pop.append(child)
        population = new_pop

        # Sync
        try:
            subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT)
            subprocess.run(["git", "commit", "-m", f"GP Gen {g} | Fitness {best['fitness']:.4f}"], cwd=PROJECT_ROOT)
            subprocess.run(["git", "push", "origin", "main"], cwd=PROJECT_ROOT)
        except: pass

if __name__ == "__main__":
    run_loop()
