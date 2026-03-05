"""
Evolution engine for generating and mutating genetic programming trees
compatible with GPTreeStrategy.
"""
import random
import json
import os
import copy
import logging
import glob
import subprocess
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

# Constants
OPERATORS = ["AND", "OR", "NOT"]
COMPARATORS = ["GREATER_THAN", "LESS_THAN", "CROSS_UP", "CROSS_DOWN"]
INDICATORS = ["RSI", "EMA", "SMA", "BB_UPPER", "BB_MIDDLE", "BB_LOWER"]

def generate_random_tree(max_depth: int, current_depth: int = 0) -> Dict[str, Any]:
    """
    Generate a random logic tree with the specified maximum depth.
    
    Args:
        max_depth: Maximum depth of the tree
        current_depth: Current depth in recursion (default 0)
        
    Returns:
        A dictionary representing a valid tree node
    """
    # If we've reached max depth, always generate a leaf (indicator)
    if current_depth >= max_depth:
        return _generate_indicator_node()
    
    # Decide what type of node to generate
    # At non-leaf nodes, we can generate operators or comparators
    choice = random.random()
    
    if choice < 0.6:
        # Generate operator node
        op = random.choice(OPERATORS)
        if op == "NOT":
            children = [generate_random_tree(max_depth, current_depth + 1)]
        else:
            children = [
                generate_random_tree(max_depth, current_depth + 1),
                generate_random_tree(max_depth, current_depth + 1)
            ]
        return {"operator": op, "children": children}
    else:
        # Generate comparator node
        comp = random.choice(COMPARATORS)
        # Generate left and right children as indicator nodes
        # We use current_depth + 1 to ensure they're leaves if max_depth is reached
        left = _generate_indicator_node()
        right = _generate_indicator_node()
        return {"primitive": comp, "left": left, "right": right}

def _generate_indicator_node() -> Dict[str, Any]:
    """
    Generate a random indicator node with appropriate parameters.
    
    Returns:
        A dictionary representing an indicator primitive node
    """
    indicator = random.choice(INDICATORS)
    parameters = {}
    
    if indicator in ["RSI", "EMA", "SMA"]:
        parameters["window"] = random.randint(7, 50)
    elif indicator in ["BB_UPPER", "BB_MIDDLE", "BB_LOWER"]:
        parameters["window"] = random.randint(10, 40)
        parameters["std"] = round(random.uniform(1.5, 3.0), 1)
    
    return {"primitive": indicator, "parameters": parameters}

def _estimate_subtree_depth(node: Dict[str, Any]) -> int:
    """
    Estimate the depth of a subtree.
    
    Args:
        node: The root of the subtree
        
    Returns:
        Estimated depth of the subtree
    """
    if "primitive" in node:
        # Indicator or comparator node
        if "left" in node:  # Comparator node
            return 1 + max(_estimate_subtree_depth(node["left"]), 
                          _estimate_subtree_depth(node["right"]))
        else:  # Indicator node
            return 1
    elif "operator" in node:
        # Operator node
        if node["operator"] == "NOT":
            return 1 + _estimate_subtree_depth(node["children"][0])
        else:
            return 1 + max(_estimate_subtree_depth(node["children"][0]),
                          _estimate_subtree_depth(node["children"][1]))
    return 1

def mutate_tree(tree: Dict[str, Any], mutation_rate: float = 0.1) -> Dict[str, Any]:
    """
    Apply mutations to a tree with the given mutation rate per node.
    
    Args:
        tree: The original tree to mutate
        mutation_rate: Probability of mutating each node (default 0.1)
        
    Returns:
        A mutated deep copy of the original tree
    """
    # Create a deep copy to avoid modifying the original
    mutated = copy.deepcopy(tree)
    
    def _mutate_node(node: Dict[str, Any]) -> None:
        """Recursively mutate nodes in the tree."""
        # Decide whether to mutate this node
        if random.random() < mutation_rate:
            _apply_mutation(node)
        
        # Recursively process children
        if "primitive" in node:
            # Check if it's a comparator node (has left/right)
            if "left" in node:
                _mutate_node(node["left"])
                _mutate_node(node["right"])
        elif "operator" in node:
            for child in node["children"]:
                _mutate_node(child)
    
    def _apply_mutation(node: Dict[str, Any]) -> None:
        """Apply a random mutation to the given node."""
        mutation_type = random.random()
        
        if "primitive" in node:
            # Indicator or comparator node
            if "parameters" in node:
                # Indicator node - point mutation
                if mutation_type < 0.4:
                    # Point mutation for parameters
                    if node["primitive"] in ["RSI", "EMA", "SMA"]:
                        # Perturb window
                        delta = random.randint(-5, 5)
                        new_window = node["parameters"]["window"] + delta
                        node["parameters"]["window"] = max(5, min(60, new_window))
                    elif node["primitive"] in ["BB_UPPER", "BB_MIDDLE", "BB_LOWER"]:
                        # Perturb window or std
                        if random.random() < 0.5:
                            delta = random.randint(-5, 5)
                            new_window = node["parameters"]["window"] + delta
                            node["parameters"]["window"] = max(5, min(60, new_window))
                        else:
                            delta = round(random.uniform(-0.5, 0.5), 1)
                            new_std = node["parameters"]["std"] + delta
                            node["parameters"]["std"] = max(1.0, min(4.0, round(new_std, 1)))
                elif mutation_type < 0.7:
                    # Subtree replacement
                    depth = _estimate_subtree_depth(node)
                    return _replace_node(node, _generate_indicator_node())
            else:
                # Comparator node
                if mutation_type < 0.4:
                    # Change comparator
                    new_comp = random.choice([c for c in COMPARATORS if c != node["primitive"]])
                    node["primitive"] = new_comp
                elif mutation_type < 0.7:
                    # Subtree replacement
                    depth = _estimate_subtree_depth(node)
                    return _replace_node(node, generate_random_tree(max(depth, 2), 0))
                elif mutation_type < 0.85:
                    # Branch swap
                    node["left"], node["right"] = node["right"], node["left"]
        elif "operator" in node:
            if mutation_type < 0.1:
                # Operator change (AND ↔ OR)
                if node["operator"] in ["AND", "OR"]:
                    node["operator"] = "OR" if node["operator"] == "AND" else "AND"
            elif mutation_type < 0.5:
                # Subtree replacement
                depth = _estimate_subtree_depth(node)
                return _replace_node(node, generate_random_tree(max(depth, 2), 0))
            elif mutation_type < 0.65:
                # Branch swap (for binary operators)
                if node["operator"] in ["AND", "OR"] and len(node["children"]) == 2:
                    node["children"][0], node["children"][1] = node["children"][1], node["children"][0]
            elif mutation_type < 0.7:
                # Insert wrapper
                if node["operator"] in ["AND", "OR"]:
                    # Create a new operator node with the current node as one child
                    new_op = random.choice(["AND", "OR"])
                    new_child = generate_random_tree(2, 0)
                    new_node = {
                        "operator": new_op,
                        "children": [copy.deepcopy(node), new_child]
                    }
                    return _replace_node(node, new_node)
    
    def _replace_node(original: Dict[str, Any], new_node: Dict[str, Any]) -> None:
        """Replace the contents of original with new_node."""
        original.clear()
        original.update(new_node)
    
    # Start mutation from the root
    _mutate_node(mutated)
    return mutated

def save_genome(genome: Dict[str, Any], path: str = "user_data/current_genome.json") -> None:
    """
    Save a genome to a JSON file.
    
    Args:
        genome: The genome dictionary to save
        path: Path to save the genome file
    """
    # Create parent directories if they don't exist
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(genome, f, indent=2)

def load_genome(path: str = "user_data/current_genome.json") -> Dict[str, Any]:
    """
    Load a genome from a JSON file.
    
    Args:
        path: Path to the genome file
        
    Returns:
        The loaded genome dictionary
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Genome file not found: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_current_genome(genome: dict) -> None:
    """
    Save the genome to user_data/current_genome.json.
    The genome should be a dictionary with 'entry_tree' and 'exit_tree' keys.
    
    Args:
        genome: The genome dictionary to save
    """
    path = "user_data/current_genome.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(genome, f, indent=2, ensure_ascii=False)
    logging.info(f"Saved genome to {path}")

def run_backtest(timerange: str = "20241101-20241115") -> bool:
    """
    Run a backtest using GPTreeStrategy.
    
    Args:
        timerange: Timerange for backtesting (default "20241101-20241115")
        
    Returns:
        True if backtest succeeded, False otherwise
    """
    command = [
        "/home/saus/freqtrade/.venv/bin/freqtrade",
        "backtesting",
        "--strategy", "GPTreeStrategy",
        "--timerange", timerange,
        "--config", "config.json",
        "--userdir", "user_data"
    ]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logging.error(f"Backtest failed with return code {result.returncode}")
            logging.error(f"STDOUT:\n{result.stdout}")
            logging.error(f"STDERR:\n{result.stderr}")
            return False
        return True
    except Exception as e:
        logging.error(f"Exception while running backtest: {e}")
        return False

def calculate_fitness() -> float:
    """
    Calculate fitness score from the most recent backtest result.
    
    Returns:
        Fitness score as float. Returns 0.0 if no valid result found.
    """
    try:
        # Find all JSON files in backtest_results directory
        pattern = "user_data/backtest_results/*.json"
        files = glob.glob(pattern)
        
        # Exclude .meta.json files
        files = [f for f in files if not f.endswith('.meta.json')]
        
        if not files:
            logging.warning("No backtest result files found")
            return 0.0
        
        # Sort by modification time (most recent first)
        files.sort(key=os.path.getmtime, reverse=True)
        latest_file = files[0]
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find the strategy result for GPTreeStrategy
        strategy_result = None
        if isinstance(data, dict) and "strategy" in data:
            # Single strategy result format
            if data.get("strategy") == "GPTreeStrategy":
                strategy_result = data
        elif isinstance(data, list):
            # Multiple strategy results format
            for item in data:
                if isinstance(item, dict) and item.get("strategy") == "GPTreeStrategy":
                    strategy_result = item
                    break
        
        if not strategy_result:
            logging.warning("GPTreeStrategy result not found in backtest results")
            return 0.0
        
        # Extract metrics
        total_trades = strategy_result.get("total_trades", 0)
        if total_trades == 0:
            logging.info("No trades executed, fitness is 0.0")
            return 0.0
        
        profit_percent = strategy_result.get("profit_total", 0.0)
        sharpe_ratio = strategy_result.get("sharpe", 0.0)
        max_drawdown_percent = abs(strategy_result.get("max_drawdown_account", 0.0))
        
        # Calculate fitness
        fitness = (profit_percent * sharpe_ratio) / (1 + abs(max_drawdown_percent))
        
        logging.info(f"Fitness: {fitness:.4f} | Trades: {total_trades}")
        return fitness
        
    except Exception as e:
        logging.error(f"Error calculating fitness: {e}")
        return 0.0

if __name__ == "__main__":
    # Setup logging
    log_path = "user_data/logs/evolution.log"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[
            logging.FileHandler(log_path, mode='a'),
            logging.StreamHandler()
        ]
    )
    
    # Generate entry and exit trees
    entry_tree = generate_random_tree(max_depth=5)
    exit_tree = generate_random_tree(max_depth=5)
    
    # Create a proper genome structure
    genome = {
        "entry_tree": entry_tree,
        "exit_tree": exit_tree
    }
    
    # Save as current genome
    save_current_genome(genome)
    logging.info("Saved new random genome with entry and exit trees. Starting backtest...")
    
    # Verify the file was saved correctly
    # Check if the file exists and has the right structure
    if not os.path.exists("user_data/current_genome.json"):
        logging.error("Genome file not found at user_data/current_genome.json")
        exit(1)
    
    # Check the contents
    with open("user_data/current_genome.json", 'r', encoding='utf-8') as f:
        saved_genome = json.load(f)
    if "entry_tree" not in saved_genome or "exit_tree" not in saved_genome:
        logging.error(f"Saved genome is missing required keys: {list(saved_genome.keys())}")
        exit(1)
    else:
        logging.info(f"Genome verified with keys: {list(saved_genome.keys())}")
    
    # Run backtest
    success = run_backtest(timerange="20241101-20241115")
    if not success:
        logging.error("Backtest failed")
        exit(1)
    
    # Calculate fitness
    fitness = calculate_fitness()
    logging.info(f"Fitness score: {fitness:.4f}")
    
    # Save genome with timestamp for history
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    history_path = f"user_data/genome_history/genome_{timestamp}_fitness_{fitness:.4f}.json"
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(genome, f, indent=2, ensure_ascii=False)
    logging.info(f"Saved historical genome to {history_path}")
