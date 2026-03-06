import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Union
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy

# Standard Pathing
try:
    from gp_blocks import *
except ImportError:
    sys.path.append(str(Path(__file__).parent))
    from gp_blocks import *

class GPTreeStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    process_only_new_candles = False
    # DISABLING ROI AND STOPLOSS TO UNBLOCK EVOLUTION
    minimal_roi = {"0": 100} 
    stoploss = -0.99
    startup_candle_count = 30

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.genome_path = Path(self.config['user_data_dir']) / "current_genome.json"
        self.genome: Dict[str, Any] = {}
        self._load_genome()

    def _load_genome(self) -> None:
        if not self.genome_path.exists():
            self.genome_path = Path(self.config['user_data_dir']) / "current_genome.json"
        with self.genome_path.open('r', encoding='utf-8') as f:
            self.genome = json.load(f)

    def evaluate_node(self, node: Dict[str, Any], dataframe: pd.DataFrame) -> pd.Series:
        if not isinstance(node, dict):
            return pd.Series(False, index=dataframe.index)

        if "constant" in node:
            try:
                # Ensure constant is a float, catching LLM strings
                val = float(node["constant"])
                return pd.Series(val, index=dataframe.index)
            except (ValueError, TypeError):
                return pd.Series(0.0, index=dataframe.index)
        
        if "primitive" in node:
            name = node["primitive"]
            params = node.get("parameters", {})
            
            # Numeric & Bool Helper Blocks
            if name in BLOCK_REGISTRY.get('num', {}) or name in BLOCK_REGISTRY.get('bool_helper', {}):
                func = BLOCK_REGISTRY.get('num', {}).get(name) or BLOCK_REGISTRY.get('bool_helper', {}).get(name)
                return func(dataframe, **params)
            
            # Comparator Blocks
            if name in BLOCK_REGISTRY.get('comparator', {}):
                l = self.evaluate_node(node.get("left", {}), dataframe)
                r = self.evaluate_node(node.get("right", {}), dataframe)
                return BLOCK_REGISTRY['comparator'][name](l, r)
        
        if "operator" in node:
            op = node["operator"].upper()
            c = node.get("children", [])
            
            if op in BLOCK_REGISTRY.get('operator', {}):
                # Dynamically evaluate children and pass them to the operator
                c_evals = [self.evaluate_node(child, dataframe) for child in c]
                # Fallback for empty/single child depending on operator requirements
                if op == "AND" and len(c_evals) >= 2:
                    return BLOCK_REGISTRY['operator'][op](c_evals[0], c_evals[1])
                elif op == "OR":
                    if len(c_evals) >= 2:
                        return BLOCK_REGISTRY['operator'][op](c_evals[0], c_evals[1])
                    elif len(c_evals) == 1:
                        return c_evals[0]
                elif op == "NOT" and len(c_evals) >= 1:
                    return BLOCK_REGISTRY['operator'][op](c_evals[0])
            
        return pd.Series(False, index=dataframe.index)

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Pre-calculate RSI to ensure it's available for the evaluation
        dataframe['rsi'] = get_rsi(dataframe, window=14)
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        try:
            # Force signals to be boolean then int
            res = self.evaluate_node(self.genome.get("entry_tree", {}), dataframe)
            dataframe['enter_long'] = res.fillna(False).astype(int)
        except Exception as e:
            log_path = Path(self.config['user_data_dir']) / "logs" / "strategy_debug.log"
            with open(log_path, "a") as f:
                f.write(f"ENTRY ERROR: {e}\n")
            dataframe['enter_long'] = 0
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        try:
            res = self.evaluate_node(self.genome.get("exit_tree", {}), dataframe)
            dataframe['exit_long'] = res.fillna(False).astype(int)
        except Exception as e:
            log_path = Path(self.config['user_data_dir']) / "logs" / "strategy_debug.log"
            with open(log_path, "a") as f:
                f.write(f"EXIT ERROR: {e}\n")
            dataframe['exit_long'] = 0
        return dataframe
