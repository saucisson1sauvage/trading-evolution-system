import pandas as pd
import pandas_ta as ta
from freqtrade.strategy import IStrategy

class SimpleVerifiedStrategy(IStrategy):
    """
    Ultra-simple strategy to verify the trade pipeline.
    Signals:
    - Buy: Close Price > SMA(20)
    - Sell: Close Price < SMA(20)
    """
    INTERFACE_VERSION = 3
    timeframe = '5m'
    process_only_new_candles = False
    minimal_roi = {"0": 0.01}
    stoploss = -0.10
    startup_candle_count = 20

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['sma'] = ta.sma(dataframe['close'], length=20)
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (dataframe['close'] > dataframe['sma']) & 
            (dataframe['volume'] > 0),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (dataframe['close'] < dataframe['sma']) & 
            (dataframe['volume'] > 0),
            'exit_long'] = 1
        return dataframe
