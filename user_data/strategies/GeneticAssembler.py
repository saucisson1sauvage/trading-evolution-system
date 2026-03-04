import json
import importlib
import logging
import sys
import pandas as pd
from typing import Dict, List
from pandas import DataFrame
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
        project_root = str(PathResolver.get_project_root())
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

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
        # Initialize enter_long column
        dataframe.loc[:, 'enter_long'] = 0
        
        # First, collect all block signals in temporary columns
        for i, block in enumerate(self.blocks):
            if hasattr(block, "populate_entry_trend"):
                # Create a temporary dataframe to avoid modifying the original
                temp_df = dataframe.copy()
                temp_df = block.populate_entry_trend(temp_df, metadata, params)
                # Store each block's signal in a temporary column
                dataframe[f'_block_{i}_entry'] = temp_df['enter_long']
        
        # Logical AND: all blocks must signal 1 to enter
        if self.blocks:
            # Start with all True
            combined_signal = pd.Series(True, index=dataframe.index)
            for i in range(len(self.blocks)):
                if hasattr(self.blocks[i], "populate_entry_trend"):
                    combined_signal = combined_signal & (dataframe[f'_block_{i}_entry'] == 1)
            # Set enter_long where all conditions are met
            dataframe.loc[combined_signal, 'enter_long'] = 1
        
        # Clean up temporary columns
        for i in range(len(self.blocks)):
            if f'_block_{i}_entry' in dataframe.columns:
                dataframe = dataframe.drop(columns=[f'_block_{i}_entry'])
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.dna.get("parameters", {})
        # Initialize exit_long column
        dataframe.loc[:, 'exit_long'] = 0
        
        # First, collect all block signals in temporary columns
        for i, block in enumerate(self.blocks):
            if hasattr(block, "populate_exit_trend"):
                # Create a temporary dataframe to avoid modifying the original
                temp_df = dataframe.copy()
                temp_df = block.populate_exit_trend(temp_df, metadata, params)
                # Store each block's signal in a temporary column
                dataframe[f'_block_{i}_exit'] = temp_df['exit_long']
        
        # Logical OR: any block signals 1 to exit
        if self.blocks:
            # Start with all False
            combined_signal = pd.Series(False, index=dataframe.index)
            for i in range(len(self.blocks)):
                if hasattr(self.blocks[i], "populate_exit_trend"):
                    combined_signal = combined_signal | (dataframe[f'_block_{i}_exit'] == 1)
            # Set exit_long where any condition is met
            dataframe.loc[combined_signal, 'exit_long'] = 1
        
        # Clean up temporary columns
        for i in range(len(self.blocks)):
            if f'_block_{i}_exit' in dataframe.columns:
                dataframe = dataframe.drop(columns=[f'_block_{i}_exit'])
        
        return dataframe
