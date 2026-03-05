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
from typing import Dict, Any, List, Optional, Tuple, Union
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
    # If we've reached max depth, always generate a leaf
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
        # Generate left child as a leaf node
        left = _generate_indicator_node()
        # For right child, prefer constants (50% chance)
        if random.random() < 0.5:
            # Generate a constant node
            right = {"constant": round(random.uniform(10, 90), 2)}
        else:
            right = _generate_indicator_node()
        return {"primitive": comp, "left": left, "right": right}

def _generate_indicator_node() -> Dict[str, Any]:
    """
    Generate a random leaf node: either an indicator or a constant.
    
    Returns:
        A dictionary representing either an indicator primitive node or a constant node
    """
    # 30% chance to generate a constant, 70% chance to generate an indicator
    if random.random() < 0.30:
        # Generate a constant value between 10 and 90, rounded to 2 decimal places
        return {"constant": round(random.uniform(10, 90), 2)}
    else:
        indicator = random.choice(INDICATORS)
        parameters = {}
        
        if indicator in ["RSI", "EMA", "SMA"]:
            parameters["window"] = random.randint(7, 50)
        elif indicator in ["BB_UPPER", "BB_MIDDLE", "BB_LOWER"]:
            parameters["window"] = random.randint(10, 40)
            parameters["std"] = round(random.uniform(1.5, 3.0), 1)
        
        return {"primitive": indicator, "parameters": parameters}

def get_all_nodes(tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collect all nodes in the tree (including the root) in a flat list.
    
    Args:
        tree: The root node of the tree
        
    Returns:
        List of all node dictionaries in depth-first order
    """
    nodes = [tree]
    if "constant" in tree:
        # Constant nodes are leaves, no children
        pass
    elif "primitive" in tree:
        # Check if it's a comparator node (has left/right)
        if "left" in tree:
            nodes.extend(get_all_nodes(tree["left"]))
            nodes.extend(get_all_nodes(tree["right"]))
    elif "operator" in tree:
        for child in tree.get("children", []):
            nodes.extend(get_all_nodes(child))
    return nodes

def get_parent_info(tree: Dict[str, Any], target_node: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Union[str, int, None]]:
    """
    Find the parent of target_node within tree and the key/index that leads to it.
    
    Args:
        tree: The root of the tree to search
        target_node: The node whose parent we want to find
        
    Returns:
        (parent_dict, key_or_index) if found, (None, None) otherwise
        key_or_index can be "left", "right", or an integer index in "children"
    """
    # Helper to compare node identity (since we're dealing with dicts)
    def nodes_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        # Simple identity check: compare memory addresses
        return id(a) == id(b)
    
    def search(node: Dict[str, Any], parent: Optional[Dict[str, Any]] = None, 
               key: Union[str, int, None] = None) -> Tuple[Optional[Dict[str, Any]], Union[str, int, None]]:
        if nodes_equal(node, target_node):
            return parent, key
        
        if "primitive" in node and "left" in node:
            # Comparator node
            left_result = search(node["left"], node, "left")
            if left_result[0] is not None:
                return left_result
            right_result = search(node["right"], node, "right")
            if right_result[0] is not None:
                return right_result
        elif "operator" in node:
            children = node.get("children", [])
            for i, child in enumerate(children):
                child_result = search(child, node, i)
                if child_result[0] is not None:
                    return child_result
        return None, None
    
    return search(tree)

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

def get_node_type(node: Dict[str, Any]) -> str:
    """
    Determine if a node returns boolean or numeric values.
    
    Args:
        node: The tree node
        
    Returns:
        "boolean" for operators and comparators, "numeric" for indicators and constants
    """
    if "constant" in node:
        return "numeric"
    elif "operator" in node:
        return "boolean"
    elif "primitive" in node:
        if node["primitive"] in COMPARATORS:
            return "boolean"
        else:
            return "numeric"
    # Should not reach here for valid nodes
    raise ValueError(f"Cannot determine node type: {node}")

def crossover_trees(tree1: Dict[str, Any], tree2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Perform subtree crossover between two trees.
    
    Args:
        tree1: First parent tree
        tree2: Second parent tree
        
    Returns:
        Two new trees (offspring1, offspring2) after crossover
    """
    # Create deep copies to avoid modifying originals
    offspring1 = copy.deepcopy(tree1)
    offspring2 = copy.deepcopy(tree2)
    
    # Get all nodes from both trees
    nodes1 = get_all_nodes(offspring1)
    nodes2 = get_all_nodes(offspring2)
    
    # Remove root nodes from selection (to avoid swapping entire trees)
    # But actually, swapping roots is valid
    # We'll allow it
    
    max_attempts = 10
    for attempt in range(max_attempts):
        # Randomly select nodes
        node1 = random.choice(nodes1)
        node2 = random.choice(nodes2)
        
        # Check if nodes have compatible types
        try:
            type1 = get_node_type(node1)
            type2 = get_node_type(node2)
        except ValueError:
            continue  # Skip invalid nodes
        
        if type1 != type2:
            continue  # Types don't match
        
        # Find parents and connection info
        parent1, key1 = get_parent_info(offspring1, node1)
        parent2, key2 = get_parent_info(offspring2, node2)
        
        # Perform swap
        if parent1 is None:
            # node1 is the root of offspring1
            offspring1 = copy.deepcopy(node2)
            # We need to update nodes1 for the second swap
            # But since we're swapping, we need to handle this carefully
            # Actually, if node1 is root, we replace the entire tree
            # So offspring1 becomes a copy of node2
            # And we need to put node1 into offspring2 at node2's position
            if parent2 is None:
                offspring2 = copy.deepcopy(node1)
            else:
                if isinstance(key2, int):
                    parent2["children"][key2] = copy.deepcopy(node1)
                elif key2 == "left":
                    parent2["left"] = copy.deepcopy(node1)
                elif key2 == "right":
                    parent2["right"] = copy.deepcopy(node1)
            break
        elif parent2 is None:
            # node2 is the root of offspring2
            offspring2 = copy.deepcopy(node1)
            if isinstance(key1, int):
                parent1["children"][key1] = copy.deepcopy(node2)
            elif key1 == "left":
                parent1["left"] = copy.deepcopy(node2)
            elif key1 == "right":
                parent1["right"] = copy.deepcopy(node2)
            break
        else:
            # Both have parents, swap normally
            # Store copies
            temp1 = copy.deepcopy(node1)
            temp2 = copy.deepcopy(node2)
            
            # Replace node1 with temp2
            if isinstance(key1, int):
                parent1["children"][key1] = temp2
            elif key1 == "left":
                parent1["left"] = temp2
            elif key1 == "right":
                parent1["right"] = temp2
            
            # Replace node2 with temp1
            if isinstance(key2, int):
                parent2["children"][key2] = temp1
            elif key2 == "left":
                parent2["left"] = temp1
            elif key2 == "right":
                parent2["right"] = temp1
            break
    else:
        # If we exhausted attempts, return the original copies without crossover
        pass
    
    return offspring1, offspring2

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
        if "constant" in node:
            # Constant nodes are leaves, no children to process
            pass
        elif "primitive" in node:
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
        
        if "constant" in node:
            # Constant node mutation
            if mutation_type < 0.5:
                # Additive mutation
                delta = random.uniform(-5, 5)
                new_val = node["constant"] + delta
                # Clamp to reasonable range [0, 100]
                node["constant"] = max(0.0, min(100.0, round(new_val, 2)))
            else:
                # Multiplicative mutation
                factor = random.uniform(0.85, 1.15)
                new_val = node["constant"] * factor
                node["constant"] = max(0.0, min(100.0, round(new_val, 2)))
        elif "primitive" in node:
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
                elif mutation_type < 0.9:
                    # Comparator swap mutation (only for comparator nodes)
                    if node["primitive"] in COMPARATORS:
                        # Choose a different comparator
                        other_comps = [c for c in COMPARATORS if c != node["primitive"]]
                        if other_comps:
                            node["primitive"] = random.choice(other_comps)
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
    from pathlib import Path
    
    # Use absolute path to ensure consistency with GPTreeStrategy's loading logic
    genome_path = Path.cwd() / "user_data" / "current_genome.json"
    genome_path.parent.mkdir(parents=True, exist_ok=True)
    
    with genome_path.open('w', encoding='utf-8') as f:
        json.dump(genome, f, indent=2, ensure_ascii=False)
    logging.info(f"Saved genome to {genome_path}")

def run_backtest(timerange: str = "20241101-20241115") -> bool:
    """
    Run a backtest using GPTreeStrategy.
    
    Args:
        timerange: Timerange for backtesting (default "20241101-20241115")
        
    Returns:
        True if backtest succeeded, False otherwise
    """
    from pathlib import Path
    
    # Use absolute path for userdir to ensure Freqtrade finds the strategy correctly
    userdir_abs = str((Path.cwd() / "user_data").resolve())
    config_path = str((Path.cwd() / "config.json").resolve())
    
    command = [
        "/home/saus/freqtrade/.venv/bin/freqtrade",
        "backtesting",
        "--strategy", "GPTreeStrategy",
        "--timerange", timerange,
        "--config", config_path,
        "--userdir", userdir_abs
    ]
    
    logging.info(f"Running backtest with command: {' '.join(command)}")
    
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

def generate_offspring(parents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a new individual from a population of parents.
    
    Args:
        parents: List of parent trees
        
    Returns:
        A new tree generated through crossover or mutation
    """
    if not parents:
        # No parents available, generate random tree
        return generate_random_tree(max_depth=5)
    
    # Decide operation
    if random.random() < 0.7 and len(parents) >= 2:
        # Crossover
        parent1, parent2 = random.sample(parents, 2)
        offspring1, offspring2 = crossover_trees(parent1, parent2)
        # Return one of the offspring at random
        return random.choice([offspring1, offspring2])
    else:
        # Mutation
        parent = random.choice(parents)
        return mutate_tree(parent, mutation_rate=0.1)

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
    
    # Test the new crossover and mutation functionality
    logging.info("Testing genetic operators...")
    
    # Generate two parent trees
    parent1 = generate_random_tree(max_depth=5)
    parent2 = generate_random_tree(max_depth=5)
    
    # Perform crossover
    offspring1, offspring2 = crossover_trees(parent1, parent2)
    logging.info("Crossover completed successfully")
    
    # Test mutation
    mutated = mutate_tree(parent1, mutation_rate=0.2)
    logging.info("Mutation completed successfully")
    
    # Test generate_offspring
    parents = [parent1, parent2]
    new_individual = generate_offspring(parents)
    logging.info("Offspring generation completed successfully")
    
    # Generate entry and exit trees using the new functionality
    entry_tree = generate_offspring(parents)
    exit_tree = generate_offspring(parents)
    
    # Create a proper genome structure
    genome = {
        "entry_tree": entry_tree,
        "exit_tree": exit_tree
    }
    
    # Save as current genome
    save_current_genome(genome)
    logging.info("Saved new genome generated with genetic operators. Starting backtest...")
    
    # Verify the file was saved correctly
    # Check if the file exists and has the right structure
    genome_path = Path.cwd() / "user_data" / "current_genome.json"
    if not genome_path.exists():
        logging.error(f"Genome file not found at {genome_path}")
        exit(1)
    
    # Check the contents
    with genome_path.open('r', encoding='utf-8') as f:
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
