import pandas as pd
from pandas import DataFrame

def populate_indicators(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    """
    Add any indicators needed for exit logic.
    """
    # This block doesn't add any indicators, just uses existing ones
    return dataframe

def populate_entry_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    """
    This block doesn't affect entry signals.
    """
    return dataframe

def populate_exit_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame:
    """
    Basic exit logic: exit when RSI is above sell_rsi threshold.
    """
    # Ensure RSI column exists
    if 'rsi' not in dataframe.columns:
        # If RSI doesn't exist, we can't apply exit logic
        return dataframe
    
    sell_rsi = params.get('sell_rsi', 70)
    
    # Initialize 'exit_long' column if it doesn't exist
    if 'exit_long' not in dataframe.columns:
        dataframe['exit_long'] = 0
    
    # Add exit signal when RSI is above the sell threshold using OR logic
    dataframe.loc[
        (dataframe['rsi'] > sell_rsi),
        'exit_long'
    ] |= 1
    
    return dataframe
