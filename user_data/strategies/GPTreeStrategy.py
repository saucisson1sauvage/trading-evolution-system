import json
import logging
from pathlib import Path
from typing import Dict, Any, Union
import pandas as pd
from freqtrade.strategy import IStrategy
from user_data.strategies.gp_blocks import *

class GPTreeStrategy(IStrategy):
    """
    Dynamic Genetic Programming strategy shell.
    Loads and executes entry/exit logic trees from user_data/current_genome.json.
    All signals are computed recursively via evaluate_node using gp_blocks primitives.
    Fault-tolerant: evaluation failures result in no signals rather than crashes.
    """
    INTERFACE_VERSION = 3
    can_short = False
    timeframe = '5m'
    minimal_roi = {"0": 0.01}
    stoploss = -0.10
    trailing_stop = False

    def __init__(self, config: dict) -> None:
        """
        Initialize the strategy and load the genome.
        
        Args:
            config: Freqtrade configuration dictionary
        """
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.genome_path = Path("user_data/current_genome.json")
        self.genome: Dict[str, Any] = {}
        self._load_genome()

    def _load_genome(self) -> None:
        """
        Load the genome JSON file and validate its structure.
        
        Raises:
            FileNotFoundError: If the genome file does not exist
            ValueError: If the genome is missing required keys
        """
        if not self.genome_path.exists():
            raise FileNotFoundError(f"Genome file not found: {self.genome_path}")
        with self.genome_path.open('r', encoding='utf-8') as f:
            self.genome = json.load(f)
        if "entry_tree" not in self.genome or "exit_tree" not in self.genome:
            raise ValueError("Genome JSON must contain keys 'entry_tree' and 'exit_tree'")

    def evaluate_node(self, node: Dict[str, Any], dataframe: pd.DataFrame) -> pd.Series:
        """
        Recursively evaluate a node in the genetic programming tree.
        
        Args:
            node: Dictionary representing a node in the tree
            dataframe: Pandas DataFrame with market data
            
        Returns:
            pd.Series: Boolean series representing the node's evaluation
            
        Raises:
            ValueError: If the node structure is invalid or contains unknown primitives/operators
        """
        if "constant" in node:
            # Return a Series broadcasting the constant value to match dataframe length
            return pd.Series(node["constant"], index=dataframe.index)
        
        if "primitive" in node:
            name = node["primitive"]
            params = node.get("parameters", {})
            if name == "RSI":
                return get_rsi(dataframe, **params)
            elif name == "EMA":
                return get_ema(dataframe, **params)
            elif name == "SMA":
                return get_sma(dataframe, **params)
            elif name in ["BB_UPPER", "BB_MIDDLE", "BB_LOWER"]:
                upper, middle, lower = get_bollinger(dataframe, **params)
                if name == "BB_UPPER": return upper
                if name == "BB_MIDDLE": return middle
                if name == "BB_LOWER": return lower
            elif name in ["GREATER_THAN", "LESS_THAN", "CROSS_UP", "CROSS_DOWN"]:
                left = self.evaluate_node(node["left"], dataframe)
                right = self.evaluate_node(node["right"], dataframe)
                if name == "GREATER_THAN": return greater_than(left, right)
                if name == "LESS_THAN": return less_than(left, right)
                if name == "CROSS_UP": return cross_up(left, right)
                if name == "CROSS_DOWN": return cross_down(left, right)
            else:
                raise ValueError(f"Unknown primitive: {name}")

        elif "operator" in node:
            op = node["operator"].upper()
            children = node.get("children", [])
            if op == "AND":
                if len(children) != 2: 
                    raise ValueError("AND requires exactly 2 children")
                return and_op(
                    self.evaluate_node(children[0], dataframe),
                    self.evaluate_node(children[1], dataframe)
                )
            elif op == "OR":
                if len(children) != 2: 
                    raise ValueError("OR requires exactly 2 children")
                return or_op(
                    self.evaluate_node(children[0], dataframe),
                    self.evaluate_node(children[1], dataframe)
                )
            elif op == "NOT":
                if len(children) != 1: 
                    raise ValueError("NOT requires exactly 1 child")
                return not_op(self.evaluate_node(children[0], dataframe))
            else:
                raise ValueError(f"Unknown operator: {op}")

        raise ValueError("Node must contain 'constant', 'primitive', or 'operator' key")

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Populate indicators required for the strategy.
        
        Args:
            dataframe: Raw data from the exchange
            metadata: Additional information about the pair
            
        Returns:
            DataFrame with added indicators
        """
        # No pre-computation needed — indicators are evaluated dynamically in evaluate_node
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Populate entry signals based on the evaluated entry tree.
        
        Args:
            dataframe: DataFrame with indicators
            metadata: Additional information about the pair
            
        Returns:
            DataFrame with 'enter_long' column added
        """
        try:
            entry_signal = self.evaluate_node(self.genome["entry_tree"], dataframe)
            dataframe['enter_long'] = entry_signal.astype(int)
        except Exception as e:
            self.logger.error(f"Entry tree evaluation failed: {str(e)}")
            dataframe['enter_long'] = 0
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Populate exit signals based on the evaluated exit tree.
        
        Args:
            dataframe: DataFrame with indicators
            metadata: Additional information about the pair
            
        Returns:
            DataFrame with 'exit_long' column added
        """
        try:
            exit_signal = self.evaluate_node(self.genome["exit_tree"], dataframe)
            dataframe['exit_long'] = exit_signal.astype(int)
        except Exception as e:
            self.logger.error(f"Exit tree evaluation failed: {str(e)}")
            dataframe['exit_long'] = 0
        return dataframe
