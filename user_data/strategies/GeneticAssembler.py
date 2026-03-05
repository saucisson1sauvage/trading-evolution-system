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
    process_only_new_candles = False
    minimal_roi = {"0": 0.01}
    stoploss = -0.25

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
        # Add project root to sys.path so we can import user_data...
        project_root = str(PathResolver.get_project_root())
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        for block_name in self.dna.get("active_blocks", []):
            try:
                # Absolute import based on project structure
                module_path = f"user_data.strategies.blocks.{block_name}"
                module = importlib.import_module(module_path)
                importlib.reload(module)
                blocks.append(module)
                logger.info(f"Successfully loaded block: {block_name}")
            except Exception as e:
                logger.error(f"Failed to load block {block_name}: {e}")
                # Try relative import if absolute fails
                try:
                    module_path = f"blocks.{block_name}"
                    module = importlib.import_module(module_path)
                    importlib.reload(module)
                    blocks.append(module)
                    logger.info(f"Successfully loaded block (relative): {block_name}")
                except Exception as e2:
                    logger.error(f"Failed to load block {block_name} (relative): {e2}")
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
        
        # Reset enter_long once at the start
        dataframe.loc[:, 'enter_long'] = 0

        for block in self.blocks:
            if hasattr(block, "populate_entry_trend"):
                # Capturing individual block signal
                dataframe = block.populate_entry_trend(dataframe, metadata, params)
                # Any block that sets enter_long=1 contributes a vote
                dataframe['enter_long_votes'] += dataframe['enter_long'].fillna(0)
                # Reset enter_long for the next block
                dataframe.loc[:, 'enter_long'] = 0
        
        # Logic Fix: Require at least 1 vote to trigger entry
        dataframe.loc[dataframe['enter_long_votes'] >= 1, 'enter_long'] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.dna.get("parameters", {})
        dataframe.loc[:, 'exit_long'] = 0
        for block in self.blocks:
            if hasattr(block, "populate_exit_trend"):
                dataframe = block.populate_exit_trend(dataframe, metadata, params)
        return dataframe
