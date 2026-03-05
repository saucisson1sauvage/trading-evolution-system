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
                print(f"Error loading block {block_name}: {e}")
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
        # Restore modular voting logic with required_votes = 1
        params = self.dna.get("parameters", {})
        dataframe.loc[:, 'enter_long'] = 0
        
        # Track votes from each block
        vote_columns = []
        for i, block in enumerate(self.blocks):
            if hasattr(block, "populate_entry_trend"):
                # Create a temporary dataframe to avoid modifying original
                temp_df = dataframe.copy()
                temp_df = block.populate_entry_trend(temp_df, metadata, params)
                # Check if the block added enter_long signals
                if 'enter_long' in temp_df.columns:
                    # Create a vote column for this block
                    vote_col = f'vote_{i}'
                    dataframe[vote_col] = temp_df['enter_long'].fillna(0).astype(int)
                    vote_columns.append(vote_col)
        
        # Sum votes and require at least 1 vote
        if vote_columns:
            dataframe['total_votes'] = dataframe[vote_columns].sum(axis=1)
            dataframe.loc[dataframe['total_votes'] >= 1, 'enter_long'] = 1
            
            # Deep-trace audit: print last 10 candles with RSI and votes
            if 'rsi' in dataframe.columns:
                # Create a display dataframe with relevant columns
                display_cols = ['date']
                if 'rsi' in dataframe.columns:
                    display_cols.append('rsi')
                display_cols.extend(vote_columns)
                display_cols.append('total_votes')
                display_cols.append('enter_long')
                
                print("DEBUG: Last 10 candles with RSI and voting state:")
                print(dataframe[display_cols].tail(10))
                
                # Also print statistics
                print(f"DEBUG: Total rows with votes >= 1: {(dataframe['total_votes'] >= 1).sum()}")
                print(f"DEBUG: Max votes: {dataframe['total_votes'].max()}")
                print(f"DEBUG: RSI range: [{dataframe['rsi'].min():.2f}, {dataframe['rsi'].max():.2f}]")
                print(f"DEBUG: RSI mean: {dataframe['rsi'].mean():.2f}")
        else:
            print("DEBUG: No voting blocks found")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.dna.get("parameters", {})
        dataframe.loc[:, 'exit_long'] = 0
        for block in self.blocks:
            if hasattr(block, "populate_exit_trend"):
                dataframe = block.populate_exit_trend(dataframe, metadata, params)
        return dataframe
