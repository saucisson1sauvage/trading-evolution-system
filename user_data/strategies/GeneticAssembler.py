import sys
from pathlib import Path
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import json
import importlib
import logging
from typing import Dict, List
from pandas import DataFrame
import numpy as np
from freqtrade.strategy import IStrategy
from scripts.paths import PathResolver

logger = logging.getLogger(__name__)

class GeneticAssembler(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    minimal_roi = {"0": 0.1}
    stoploss = -0.10

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.dna_path = PathResolver.get_strategies_path() / "dna.json"
        self.dna = self._load_dna()
        self.blocks = self._load_blocks()

    def _load_dna(self) -> dict:
        try:
            with open(self.dna_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load DNA from {self.dna_path}: {e}")
            return {"active_blocks": [], "parameters": {}}

    def _load_blocks(self):
        blocks = []
        for block_name in self.dna.get("active_blocks", []):
            try:
                module_path = f"user_data.strategies.blocks.{block_name}"
                module = importlib.import_module(module_path)
                importlib.reload(module)
                blocks.append(module)
                logger.info(f"Loaded block: {block_name}")
            except Exception as e:
                logger.error(f"Failed to load block {block_name}: {e}")
        return blocks

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.dna.get("parameters", {})
        for block in self.blocks:
            if hasattr(block, "populate_indicators"):
                dataframe = block.populate_indicators(dataframe, metadata, params)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.dna.get("parameters", {})
        # Voting system: Count how many blocks signal entry
        dataframe.loc[:, 'enter_long_votes'] = 0
        
        for block in self.blocks:
            if hasattr(block, "populate_entry_trend"):
                # Reset enter_long before each block to capture its individual output
                dataframe.loc[:, 'enter_long'] = 0
                dataframe = block.populate_entry_trend(dataframe, metadata, params)
                # Increment votes based on this block's output
                dataframe['enter_long_votes'] += dataframe['enter_long'].fillna(0)
        
        # Reset enter_long one final time
        dataframe.loc[:, 'enter_long'] = 0
        
        # Require at least 2 votes (or all available if less than 2)
        # This increases trade frequency as requested
        num_blocks = len(self.blocks)
        required_votes = min(2, num_blocks) if num_blocks > 0 else 1
        dataframe.loc[dataframe['enter_long_votes'] >= required_votes, 'enter_long'] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.dna.get("parameters", {})
        dataframe.loc[:, 'exit_long'] = 0
        for block in self.blocks:
            if hasattr(block, "populate_exit_trend"):
                dataframe = block.populate_exit_trend(dataframe, metadata, params)
        return dataframe
