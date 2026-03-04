import pandas_ta as ta
from pandas import DataFrame

def populate_indicators(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    dataframe['rsi'] = ta.rsi(dataframe['close'], length=params.get('rsi_period', 14))
    return dataframe

def populate_entry_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    dataframe.loc[
        (
            (dataframe['rsi'] < params.get('buy_rsi', 30)) &
            (dataframe['volume'] > 0)
        ),
        'enter_long'] = 1
    return dataframe

def populate_exit_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    dataframe.loc[
        (
            (dataframe['rsi'] > params.get('sell_rsi', 70)) &
            (dataframe['volume'] > 0)
        ),
        'exit_long'] = 1
    return dataframe
