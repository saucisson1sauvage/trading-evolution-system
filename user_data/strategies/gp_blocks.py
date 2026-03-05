import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Union, Tuple

def get_rsi(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    Calculate the Relative Strength Index (RSI) for the given DataFrame.
    Returns a pd.Series with RSI values.
    """
    return ta.rsi(close=df['close'], length=window)

def get_ema(df: pd.DataFrame, window: int) -> pd.Series:
    """
    Calculate the Exponential Moving Average (EMA) for the given DataFrame.
    Returns a pd.Series with EMA values.
    """
    return ta.ema(close=df['close'], length=window)

def get_sma(df: pd.DataFrame, window: int) -> pd.Series:
    """
    Calculate the Simple Moving Average (SMA) for the given DataFrame.
    Returns a pd.Series with SMA values.
    """
    return ta.sma(close=df['close'], length=window)

def get_bollinger(df: pd.DataFrame, window: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands (upper, middle, lower) for the given DataFrame.
    Returns a tuple of three pd.Series: (upper_band, middle_band, lower_band).
    """
    bb = ta.bbands(close=df['close'], length=window, std=std)
    return bb[f'BBU_{window}_{std}'], bb[f'BBM_{window}_{std}'], bb[f'BBL_{window}_{std}']

def greater_than(s1: pd.Series, s2: Union[pd.Series, float, int]) -> pd.Series:
    """
    Element-wise comparison: s1 > s2.
    Returns a boolean pd.Series indicating where s1 is greater than s2.
    """
    return s1 > s2

def less_than(s1: pd.Series, s2: Union[pd.Series, float, int]) -> pd.Series:
    """
    Element-wise comparison: s1 < s2.
    Returns a boolean pd.Series indicating where s1 is less than s2.
    """
    return s1 < s2

def cross_up(s1: pd.Series, threshold: Union[pd.Series, float, int]) -> pd.Series:
    """
    Detect upward crossings where s1 crosses above threshold.
    Returns a boolean pd.Series indicating upward crossing points.
    """
    return (s1.shift(1) <= threshold) & (s1 > threshold)

def cross_down(s1: pd.Series, threshold: Union[pd.Series, float, int]) -> pd.Series:
    """
    Detect downward crossings where s1 crosses below threshold.
    Returns a boolean pd.Series indicating downward crossing points.
    """
    return (s1.shift(1) >= threshold) & (s1 < threshold)

if __name__ == "__main__":
    print("GP Blocks library loaded.")
