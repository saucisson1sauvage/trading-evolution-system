import pandas_ta as ta
from pandas import DataFrame
import numpy as np

def populate_indicators(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    dataframe['rsi'] = ta.rsi(dataframe['close'], length=params.get('rsi_period', 14))
    # Requirement: Fix NaN issues discovered during audit
    dataframe['rsi'] = dataframe['rsi'].fillna(50)
    return dataframe

def populate_entry_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    buy_threshold = params.get('buy_rsi', 30)
    # Real modular logic
    dataframe.loc[
        (
            (dataframe['rsi'] < buy_threshold) &
            (dataframe['volume'] > 0)
        ),
        'enter_long'] = 1
    return dataframe

def populate_exit_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    sell_threshold = params.get('sell_rsi', 70)
    dataframe.loc[
        (
            (dataframe['rsi'] > sell_threshold) &
            (dataframe['volume'] > 0)
        ),
        'exit_long'] = 1
    return dataframe
