import pandas as pd
import pandas_ta as ta
from pandas import DataFrame

def populate_indicators(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # EMA parameters
    ema_fast = params.get('ema_fast', 9)
    ema_slow = params.get('ema_slow', 20)
    
    # Calculate EMAs
    dataframe['ema_fast'] = ta.ema(dataframe['close'], length=ema_fast)
    dataframe['ema_slow'] = ta.ema(dataframe['close'], length=ema_slow)
    
    return dataframe

def populate_entry_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # Entry condition: fast EMA crosses above slow EMA
    dataframe.loc[
        (
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1)) &
            (dataframe['volume'] > 0)
        ),
        'enter_long'] = 1
    
    return dataframe

def populate_exit_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # Exit condition: fast EMA crosses below slow EMA
    dataframe.loc[
        (
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1)) &
            (dataframe['volume'] > 0)
        ),
        'exit_long'] = 1
    
    return dataframe
