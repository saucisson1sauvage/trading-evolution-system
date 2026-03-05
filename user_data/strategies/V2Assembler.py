import importlib
import sys
import logging
from pathlib import Path
from typing import Dict

import pandas as pd
from pandas import DataFrame

from decimal import Decimal
from freqtrade.strategy import IStrategy

# Import PathResolver from our scripts
try:
    # Add the scripts directory to sys.path
    import sys
    from pathlib import Path
    scripts_path = Path(__file__).parent.parent / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.append(str(scripts_path))
    from paths import PathResolver
except ImportError:
    # Fallback if PathResolver is not available
    class PathResolver:
        @staticmethod
        def get_strategies_path() -> Path:
            return Path(__file__).parent
        
        @staticmethod
        def get_project_root() -> Path:
            # Go up two levels from the strategies directory
            return Path(__file__).parent.parent.parent

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
    # Set to at least the maximum indicator period used in blocks
    startup_candle_count: int = 100

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
        
        # Try multiple possible locations for config_v2.json
        possible_paths = []
        
        # 1. Try PathResolver.get_project_root()
        try:
            project_root = PathResolver.get_project_root()
            possible_paths.append(project_root / "config_v2.json")
        except Exception as e:
            self.logger.debug(f"Could not get project root: {e}")
        
        # 2. Try current strategy directory
        current_dir = Path(__file__).parent
        possible_paths.append(current_dir / "config_v2.json")
        
        # 3. Try parent directory
        possible_paths.append(current_dir.parent / "config_v2.json")
        
        # 4. Try current working directory
        possible_paths.append(Path.cwd() / "config_v2.json")
        
        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break
        
        if config_path is None:
            self.logger.error("config_v2.json not found in any of the searched locations!")
            return {
                "active_blocks": [],
                "parameters": {}
            }
        
        self.logger.info(f"Loading config from: {config_path}")
        with open(config_path, 'r') as f:
            return json.load(f)

    def _load_blocks(self) -> None:
        """Dynamically import all active blocks"""
        active_blocks = self.config_v2.get('active_blocks', [])
        
        # Get the blocks directory path
        strategies_path = PathResolver.get_strategies_path()
        blocks_path = strategies_path / "blocks"
        
        # Ensure the blocks directory exists
        if not blocks_path.exists():
            self.logger.error(f"Blocks directory does not exist: {blocks_path}")
            return
        
        # Add the blocks directory to sys.path to ensure imports work
        # Use append instead of insert to avoid shadowing standard libraries
        if str(blocks_path) not in sys.path:
            sys.path.append(str(blocks_path))
        
        for block_name in active_blocks:
            try:
                # Import the module directly from the blocks directory
                module = importlib.import_module(block_name)
                self.blocks[block_name] = module
                self.logger.info(f"Successfully loaded block: {block_name}")
            except ModuleNotFoundError as e:
                self.logger.error(f"Failed to load block {block_name}: {e}")
                # Try alternative approach: import using the full module path
                try:
                    # Remove .py extension if present
                    if block_name.endswith('.py'):
                        block_name = block_name[:-3]
                    # Try to import as a module relative to the project
                    # First, get the project root
                    project_root = PathResolver.get_project_root()
                    # Calculate the relative path from project root to blocks
                    # This assumes the structure: project_root/user_data/strategies/blocks/
                    # We need to add the project root to sys.path
                    if str(project_root) not in sys.path:
                        sys.path.append(str(project_root))
                    # Import using the full path
                    module_path = f"user_data.strategies.blocks.{block_name}"
                    module = importlib.import_module(module_path)
                    self.blocks[block_name] = module
                    self.logger.info(f"Successfully loaded block {block_name} via full path")
                except Exception as e2:
                    self.logger.error(f"All attempts to load block {block_name} failed: {e2}")
            except Exception as e:
                self.logger.error(f"Unexpected error loading block {block_name}: {e}")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add indicators to the dataframe by calling each block's populate_indicators function.
        """
        params = self.config_v2.get('parameters', {})
        active_blocks = self.config_v2.get('active_blocks', [])
        
        for block_name in active_blocks:
            module = self.blocks.get(block_name)
            if module is None:
                continue
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
        active_blocks = self.config_v2.get('active_blocks', [])
        
        # Initialize entry columns if they don't exist
        if 'enter_long' not in dataframe.columns:
            dataframe['enter_long'] = 0
        if 'enter_short' not in dataframe.columns:
            dataframe['enter_short'] = 0
        
        for block_name in active_blocks:
            module = self.blocks.get(block_name)
            if module is None:
                continue
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
        active_blocks = self.config_v2.get('active_blocks', [])
        
        # Initialize exit columns if they don't exist
        if 'exit_long' not in dataframe.columns:
            dataframe['exit_long'] = 0
        if 'exit_short' not in dataframe.columns:
            dataframe['exit_short'] = 0
        
        for block_name in active_blocks:
            module = self.blocks.get(block_name)
            if module is None:
                continue
            try:
                if hasattr(module, 'populate_exit_trend'):
                    dataframe = module.populate_exit_trend(dataframe, metadata, params)
                    self.logger.debug(f"Applied populate_exit_trend from {block_name}")
            except Exception as e:
                self.logger.error(f"Error in populate_exit_trend for {block_name}: {e}")
        
        return dataframe
