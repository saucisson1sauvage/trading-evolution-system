import pandas as pd
import pandas_ta as ta
from pandas import DataFrame

def populate_indicators(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # MACD parameters
    macd_fast = params.get('macd_fast', 12)
    macd_slow = params.get('macd_slow', 26)
    macd_signal = params.get('macd_signal', 9)
    
    # Calculate MACD
    macd = ta.macd(dataframe['close'], fast=macd_fast, slow=macd_slow, signal=macd_signal)
    # Add MACD columns to dataframe
    dataframe['macd'] = macd[f'MACD_{macd_fast}_{macd_slow}_{macd_signal}']
    dataframe['macd_signal'] = macd[f'MACDs_{macd_fast}_{macd_slow}_{macd_signal}']
    dataframe['macd_hist'] = macd[f'MACDh_{macd_fast}_{macd_slow}_{macd_signal}']
    
    return dataframe

def populate_entry_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # MACD buy condition: MACD crosses above signal line
    dataframe.loc[
        (
            (dataframe['macd'] > dataframe['macd_signal']) &
            (dataframe['macd'].shift(1) <= dataframe['macd_signal'].shift(1))
        ),
        'enter_long'] = 1
    
    return dataframe

def populate_exit_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # MACD sell condition: MACD crosses below signal line
    dataframe.loc[
        (
            (dataframe['macd'] < dataframe['macd_signal']) &
            (dataframe['macd'].shift(1) >= dataframe['macd_signal'].shift(1))
        ),
        'exit_long'] = 1
    
    return dataframe
