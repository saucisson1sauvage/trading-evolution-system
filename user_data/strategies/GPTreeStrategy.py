import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Union
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy

# Freqtrade standard pathing for user_data/strategies
try:
    from gp_blocks import *
except ImportError:
    # Fallback for direct execution
    sys.path.append(str(Path(__file__).parent))
    from gp_blocks import *

class GPTreeStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    process_only_new_candles = False
    minimal_roi = {"0": 0.01}
    stoploss = -0.25
    startup_candle_count = 30

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        # Fixed Absolute Path for the genome
        self.genome_path = Path("/home/saus/crypto-crew-4.0/user_data/current_genome.json")
        self.genome: Dict[str, Any] = {}
        self._load_genome()

    def _load_genome(self) -> None:
        if not self.genome_path.exists():
            # Fallback to local user_data if absolute fails (e.g. migration)
            self.genome_path = Path(self.config['user_data_dir']) / "current_genome.json"
        
        with self.genome_path.open('r', encoding='utf-8') as f:
            self.genome = json.load(f)

    def evaluate_node(self, node: Dict[str, Any], dataframe: pd.DataFrame) -> pd.Series:
        if "constant" in node:
            return pd.Series(node["constant"], index=dataframe.index)
        
        if "primitive" in node:
            name = node["primitive"]
            params = node.get("parameters", {})
            if name == "RSI": return get_rsi(dataframe, **params)
            if name == "EMA": return get_ema(dataframe, **params)
            if name == "SMA": return get_sma(dataframe, **params)
            if name in ["BB_UPPER", "BB_MIDDLE", "BB_LOWER"]:
                u, m, l = get_bollinger(dataframe, **params)
                return u if name == "BB_UPPER" else (m if name == "BB_MIDDLE" else l)
            
            if name in ["GREATER_THAN", "LESS_THAN", "CROSS_UP", "CROSS_DOWN"]:
                l = self.evaluate_node(node["left"], dataframe)
                r = self.evaluate_node(node["right"], dataframe)
                if name == "GREATER_THAN": return greater_than(l, r)
                if name == "LESS_THAN": return less_than(l, r)
                if name == "CROSS_UP": return cross_up(l, r)
                if name == "CROSS_DOWN": return cross_down(l, r)
        
        if "operator" in node:
            op = node["operator"].upper()
            c = node.get("children", [])
            if op == "AND": return and_op(self.evaluate_node(c[0], dataframe), self.evaluate_node(c[1], dataframe))
            if op == "OR": return or_op(self.evaluate_node(c[0], dataframe), self.evaluate_node(c[1], dataframe))
            if op == "NOT": return not_op(self.evaluate_node(c[0], dataframe))
            
        return pd.Series(False, index=dataframe.index)

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        try:
            dataframe['enter_long'] = self.evaluate_node(self.genome["entry_tree"], dataframe).astype(int)
        except Exception as e:
            dataframe['enter_long'] = 0
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        try:
            dataframe['exit_long'] = self.evaluate_node(self.genome["exit_tree"], dataframe).astype(int)
        except Exception:
            dataframe['exit_long'] = 0
        return dataframe
