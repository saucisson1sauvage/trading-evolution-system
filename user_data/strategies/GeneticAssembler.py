import sys
from pathlib import Path
import json
import importlib
from typing import Dict, List
from pandas import DataFrame
import numpy as np
from freqtrade.strategy import IStrategy

# Standard Pathing
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))
from scripts.paths import PathResolver

class GeneticAssembler(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    process_only_new_candles = False
    minimal_roi = {"0": 0.01}
    stoploss = -0.25
    startup_candle_count = 30
    
    # HARDCODED OVERRIDE
    max_open_trades = 3

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.dna_path = PathResolver.get_strategies_path() / "dna.json"
        self.dna = self._load_dna()
        self.blocks = self._load_blocks()

    def _load_dna(self) -> dict:
        try:
            with open(self.dna_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {"active_blocks": [], "parameters": {}}

    def _load_blocks(self):
        blocks = []
        for block_name in self.dna.get("active_blocks", []):
            try:
                module_path = f"user_data.strategies.blocks.{block_name}"
                module = importlib.import_module(module_path)
                importlib.reload(module)
                blocks.append(module)
            except Exception as e:
        return blocks

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.dna.get("parameters", {})
        dataframe['enter_long'] = 0
        dataframe['exit_long'] = 0
        for block in self.blocks:
            if hasattr(block, "populate_indicators"):
                dataframe = block.populate_indicators(dataframe, metadata, params)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.dna.get("parameters", {})
        dataframe.loc[:, 'enter_long_votes'] = 0
        
        for block in self.blocks:
            if hasattr(block, "populate_entry_trend"):
                dataframe.loc[:, 'enter_long'] = 0
                dataframe = block.populate_entry_trend(dataframe, metadata, params)
                dataframe['enter_long_votes'] += dataframe['enter_long'].fillna(0)
        
        # Ensure we set enter_long to 1 if any block voted
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[dataframe['enter_long_votes'] >= 1, 'enter_long'] = 1
        
        # CRITICAL DEBUG: Is enter_long actually 1?
        signal_count = dataframe['enter_long'].sum()
        if signal_count > 0:
        else:
            
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.dna.get("parameters", {})
        dataframe.loc[:, 'exit_long'] = 0
        for block in self.blocks:
            if hasattr(block, "populate_exit_trend"):
                dataframe = block.populate_exit_trend(dataframe, metadata, params)
        return dataframe
