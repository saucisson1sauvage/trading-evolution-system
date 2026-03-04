import json
import importlib
import logging
import sys
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
        dataframe.loc[:, 'enter_long'] = 0
        for block in self.blocks:
            if hasattr(block, "populate_entry_trend"):
                dataframe = block.populate_entry_trend(dataframe, metadata, params)
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        params = self.dna.get("parameters", {})
        dataframe.loc[:, 'exit_long'] = 0
        for block in self.blocks:
            if hasattr(block, "populate_exit_trend"):
                dataframe = block.populate_exit_trend(dataframe, metadata, params)
        return dataframe
