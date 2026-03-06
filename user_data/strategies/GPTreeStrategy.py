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
        self.genome_path = Path("/home/saus/crypto-crew-4.0/user_data/current_genome.json")
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
            # Indicators
            if name == "RSI": return get_rsi(dataframe, **params)
            if name == "EMA": return get_ema(dataframe, **params)
            if name == "SMA": return get_sma(dataframe, **params)
            if name in ["BB_UPPER", "BB_MIDDLE", "BB_LOWER"]:
                u, m, l = get_bollinger(dataframe, **params)
                return u if name == "BB_UPPER" else (m if name == "BB_MIDDLE" else l)
            
            # Additional Blocks from gp_blocks.py
            if name == "TRENDING_UP": return is_trending_up(dataframe, **params)
            if name == "TRENDING_DOWN": return is_trending_down(dataframe, **params)
            if name == "VOLATILE": return is_volatile(dataframe, **params)
            if name == "VOLUME_SPIKE": return volume_spike(dataframe, **params)
            
            # Comparators
            if name in ["GREATER_THAN", "LESS_THAN", "CROSS_UP", "CROSS_DOWN"]:
                l = self.evaluate_node(node.get("left", {}), dataframe)
                r = self.evaluate_node(node.get("right", {}), dataframe)
                if name == "GREATER_THAN": return greater_than(l, r)
                if name == "LESS_THAN": return less_than(l, r)
                if name == "CROSS_UP": return cross_up(l, r)
                if name == "CROSS_DOWN": return cross_down(l, r)
        
        if "operator" in node:
            op = node["operator"].upper()
            c = node.get("children", [])
            if op == "AND": 
                if len(c) >= 2: return and_op(self.evaluate_node(c[0], dataframe), self.evaluate_node(c[1], dataframe))
                return pd.Series(False, index=dataframe.index)
            if op == "OR": 
                if len(c) >= 2: return or_op(self.evaluate_node(c[0], dataframe), self.evaluate_node(c[1], dataframe))
                if len(c) == 1: return self.evaluate_node(c[0], dataframe)
                return pd.Series(False, index=dataframe.index)
            if op == "NOT": 
                if len(c) >= 1: return not_op(self.evaluate_node(c[0], dataframe))
                return pd.Series(False, index=dataframe.index)
            
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
            with open("/home/saus/crypto-crew-4.0/user_data/logs/strategy_debug.log", "a") as f:
                f.write(f"ENTRY ERROR: {e}\n")
            dataframe['enter_long'] = 0
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        try:
            res = self.evaluate_node(self.genome.get("exit_tree", {}), dataframe)
            dataframe['exit_long'] = res.fillna(False).astype(int)
        except Exception as e:
            with open("/home/saus/crypto-crew-4.0/user_data/logs/strategy_debug.log", "a") as f:
                f.write(f"EXIT ERROR: {e}\n")
            dataframe['exit_long'] = 0
        return dataframe
