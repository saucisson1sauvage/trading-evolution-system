import pandas as pd
import pandas_ta as ta
from pandas import DataFrame

def populate_indicators(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # Bollinger Bands parameters
    bb_length = params.get('bb_length', 20)
    bb_std = params.get('bb_std', 2.0)
    
    # Calculate Bollinger Bands
    bollinger = ta.bbands(dataframe['close'], length=bb_length, std=bb_std)
    # Add Bollinger Bands columns to dataframe
    dataframe['bb_lower'] = bollinger[f'BBL_{bb_length}_{bb_std}']
    dataframe['bb_middle'] = bollinger[f'BBM_{bb_length}_{bb_std}']
    dataframe['bb_upper'] = bollinger[f'BBU_{bb_length}_{bb_std}']
    
    return dataframe

def populate_entry_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # Entry condition: close price below lower Bollinger Band
    dataframe.loc[
        (
            (dataframe['close'] < dataframe['bb_lower']) &
            (dataframe['volume'] > 0)
        ),
        'enter_long'] = 1
    
    return dataframe

def populate_exit_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # Exit condition: close price above upper Bollinger Band
    dataframe.loc[
        (
            (dataframe['close'] > dataframe['bb_upper']) &
            (dataframe['volume'] > 0)
        ),
        'exit_long'] = 1
    
    return dataframe
