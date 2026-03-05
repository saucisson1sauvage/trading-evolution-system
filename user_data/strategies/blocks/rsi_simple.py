import pandas_ta as ta
from pandas import DataFrame
import numpy as np

def populate_indicators(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    rsi_period = params.get('rsi_period', 14)
    # Calculate RSI
    dataframe['rsi'] = ta.rsi(dataframe['close'], length=rsi_period)
    
    # Deep audit: Check for NaN before and after fill
    nan_before = dataframe['rsi'].isna().sum()
    dataframe['rsi'] = dataframe['rsi'].fillna(50)
    nan_after = dataframe['rsi'].isna().sum()
    
    # Print debug info
    print(f"RSI BLOCK DEBUG: period={rsi_period}, NaN before fill: {nan_before}, after fill: {nan_after}")
    print(f"RSI BLOCK DEBUG: RSI sample values (last 5): {dataframe['rsi'].tail(5).tolist()}")
    
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
    # According to requirements, exit is handled by other blocks
    # So return the dataframe unchanged
    return dataframe
