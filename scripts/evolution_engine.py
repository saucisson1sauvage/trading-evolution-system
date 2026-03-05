import random
import json
import os
import copy
import logging
import glob
import subprocess
import time
import sys
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path("/home/saus/crypto-crew-4.0")
sys.path.append(str(PROJECT_ROOT))

# Constants
OPERATORS = ["AND", "OR", "NOT"]
COMPARATORS = ["GREATER_THAN", "LESS_THAN", "CROSS_UP", "CROSS_DOWN"]
INDICATORS = ["RSI", "EMA", "SMA", "BB_UPPER", "BB_MIDDLE", "BB_LOWER"]

def generate_random_tree(max_depth: int, current_depth: int = 0) -> Dict[str, Any]:
    if current_depth >= max_depth: return _generate_indicator_node()
    choice = random.random()
    if choice < 0.6:
        op = random.choice(OPERATORS)
        children = [generate_random_tree(max_depth, current_depth+1)] if op == "NOT" else \
                   [generate_random_tree(max_depth, current_depth+1), generate_random_tree(max_depth, current_depth+1)]
        return {"operator": op, "children": children}
    else:
        return {"primitive": random.choice(COMPARATORS), "left": _generate_indicator_node(), "right": _generate_indicator_node()}

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

def get_random_timerange() -> str:
    # 2024-11-01 to 2024-11-15 is verified data
    return "20241101-20241115"

def run_backtest(timerange: str = "20241101-20241115") -> bool:
    command = [
        "/home/saus/freqtrade/.venv/bin/freqtrade", "backtesting",
        "--strategy", "GPTreeStrategy",
        "--timerange", timerange,
        "--config", str(PROJECT_ROOT / "config.json"),
        "--userdir", str(PROJECT_ROOT / "user_data"),
        "--export", "trades",
        "--notes", "evolution_engine"
    ]
    try:
        res = subprocess.run(command, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Freqtrade Error: {res.stderr}")
            return False
        return True
    except Exception as e:
        print(f"System Error: {e}")
        return False

def calculate_fitness() -> float:
    # Search for the exported file in the results dir
    pattern = str(PROJECT_ROOT / "user_data/backtest_results/evolution_engine")
    if not os.path.exists(pattern):
        # Fallback: Find the most recent json if filename failed
        files = glob.glob(str(PROJECT_ROOT / "user_data/backtest_results/*.json"))
        if not files: return 0.0
        pattern = max(files, key=os.path.getmtime)

    try:
        with open(pattern, 'r') as f:
            data = json.load(f)
        
        # Handle different Freqtrade output formats
        res = data[0] if isinstance(data, list) else data.get("strategy", {}).get("GPTreeStrategy", data)
        if res.get("total_trades", 0) == 0: return 0.0
        
        profit = res.get("profit_total", 0.0)
        sharpe = res.get("sharpe", 0.0)
        drawdown = abs(res.get("max_drawdown_account", 0.0))
        return (profit * sharpe) / (1 + drawdown)
    except Exception as e:
        print(f"Parsing error: {e}")
        return 0.0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    genome = {"entry_tree": generate_random_tree(3), "exit_tree": generate_random_tree(2)}
    save_current_genome(genome)
    logging.info("Testing Backtest Pipe...")
    if run_backtest():
        fitness = calculate_fitness()
        logging.info(f"Pipeline Success! Fitness: {fitness:.4f}")
    else:
        logging.error("Pipeline Failed.")
