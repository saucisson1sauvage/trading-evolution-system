import importlib
import sys
import os
import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy, Decimal, TemporalParameter, IntParameter, \
    CategoricalParameter, stoploss_from_open, RealParameter

# Import PathResolver from our scripts
try:
    from scripts.paths import PathResolver
except ImportError:
    # Fallback if PathResolver is not available
    class PathResolver:
        @staticmethod
        def get_strategies_path() -> Path:
            return Path(__file__).parent

class V2Assembler(IStrategy):
    INTERFACE_VERSION = 3

    # Strategy configuration
    timeframe = '5m'
    can_short = False

    # Minimal ROI designed for the strategy
    minimal_roi = {
        "0": 0.1
    }

    # Optimal stoploss
    stoploss = -0.1

    # Trailing stop
    trailing_stop = False
    trailing_stop_positive = 0.0
    trailing_stop_positive_offset = 0.0
    trailing_only_offset_is_reached = False

    # Run "populate_indicators()" only for new candle
    process_only_new_candles = True

    # These values can be overridden in the config
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 0

    # Optional order type mapping
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'limit',
        'stoploss_on_exchange': False
    }

    # Optional order time in force
    order_time_in_force = {
        'entry': 'GTC',
        'exit': 'GTC'
    }

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Load config_v2.json
        self.config_v2 = self._load_config_v2()
        
        # Initialize blocks
        self.blocks: Dict[str, any] = {}
        self._load_blocks()

    def _load_config_v2(self) -> dict:
        """Load the V2 configuration from config_v2.json"""
        import json
        from pathlib import Path
        
        # Try to find config_v2.json in the project root
        try:
            project_root = PathResolver.get_project_root()
            config_path = project_root / "config_v2.json"
        except:
            # Fallback to current directory
            config_path = Path("config_v2.json")
        
        if not config_path.exists():
            self.logger.error("config_v2.json not found!")
            return {
                "active_blocks": [],
                "parameters": {}
            }
        
        with open(config_path, 'r') as f:
            return json.load(f)

    def _load_blocks(self) -> None:
        """Dynamically import all active blocks"""
        active_blocks = self.config_v2.get('active_blocks', [])
        
        # Get the blocks directory path
        strategies_path = PathResolver.get_strategies_path()
        blocks_path = strategies_path / "blocks"
        
        # Add the blocks directory to sys.path to ensure imports work
        if str(blocks_path) not in sys.path:
            sys.path.insert(0, str(blocks_path))
        
        for block_name in active_blocks:
            try:
                # Import the module
                module = importlib.import_module(block_name)
                self.blocks[block_name] = module
                self.logger.info(f"Successfully loaded block: {block_name}")
            except ModuleNotFoundError as e:
                self.logger.error(f"Failed to load block {block_name}: {e}")
                # Try to log the current sys.path for debugging
                self.logger.debug(f"Current sys.path: {sys.path}")
            except Exception as e:
                self.logger.error(f"Unexpected error loading block {block_name}: {e}")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add indicators to the dataframe by calling each block's populate_indicators function.
        """
        params = self.config_v2.get('parameters', {})
        
        for block_name, module in self.blocks.items():
            try:
                if hasattr(module, 'populate_indicators'):
                    dataframe = module.populate_indicators(dataframe, metadata, params)
                    self.logger.debug(f"Applied populate_indicators from {block_name}")
            except Exception as e:
                self.logger.error(f"Error in populate_indicators for {block_name}: {e}")
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Set entry signals by calling each block's populate_entry_trend function.
        """
        params = self.config_v2.get('parameters', {})
        
        # Initialize entry columns if they don't exist
        if 'enter_long' not in dataframe.columns:
            dataframe['enter_long'] = 0
        if 'enter_short' not in dataframe.columns:
            dataframe['enter_short'] = 0
        
        for block_name, module in self.blocks.items():
            try:
                if hasattr(module, 'populate_entry_trend'):
                    dataframe = module.populate_entry_trend(dataframe, metadata, params)
                    self.logger.debug(f"Applied populate_entry_trend from {block_name}")
            except Exception as e:
                self.logger.error(f"Error in populate_entry_trend for {block_name}: {e}")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Set exit signals by calling each block's populate_exit_trend function.
        """
        params = self.config_v2.get('parameters', {})
        
        # Initialize exit columns if they don't exist
        if 'exit_long' not in dataframe.columns:
            dataframe['exit_long'] = 0
        if 'exit_short' not in dataframe.columns:
            dataframe['exit_short'] = 0
        
        for block_name, module in self.blocks.items():
            try:
                if hasattr(module, 'populate_exit_trend'):
                    dataframe = module.populate_exit_trend(dataframe, metadata, params)
                    self.logger.debug(f"Applied populate_exit_trend from {block_name}")
            except Exception as e:
                self.logger.error(f"Error in populate_exit_trend for {block_name}: {e}")
        
        return dataframe
