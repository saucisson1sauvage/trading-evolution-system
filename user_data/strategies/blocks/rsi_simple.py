import pandas_ta as ta
from pandas import DataFrame

def populate_indicators(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    dataframe['rsi'] = ta.rsi(dataframe['close'], length=params.get('rsi_period', 14))
    return dataframe

def populate_entry_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # Use DNA params: buy_rsi
    buy_threshold = params.get('buy_rsi', 30)
    dataframe.loc[
        (
            (dataframe['rsi'] < buy_threshold) &
            (dataframe['volume'] > 0)
        ),
        'enter_long'] = 1
    return dataframe

def populate_exit_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    # Use DNA params: sell_rsi
    sell_threshold = params.get('sell_rsi', 70)
    dataframe.loc[
        (
            (dataframe['rsi'] > sell_threshold) &
            (dataframe['volume'] > 0)
        ),
        'exit_long'] = 1
    return dataframe
