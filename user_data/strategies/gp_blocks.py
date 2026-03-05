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

def and_op(b1: pd.Series, b2: pd.Series) -> pd.Series:
    """
    Element-wise logical AND between two boolean Series.
    Returns a boolean pd.Series where both conditions are true.
    """
    return b1 & b2

def or_op(b1: pd.Series, b2: pd.Series) -> pd.Series:
    """
    Element-wise logical OR between two boolean Series.
    Returns a boolean pd.Series where at least one condition is true.
    """
    return b1 | b2

def not_op(b: pd.Series) -> pd.Series:
    """
    Element-wise logical NOT of a boolean Series.
    Returns a boolean pd.Series with inverted truth values.
    """
    return ~b

def is_trending_up(df: pd.DataFrame, window: int = 50) -> pd.Series:
    """
    Detect uptrend by checking if close price is above EMA.
    Returns a boolean pd.Series indicating uptrend periods.
    """
    ema = get_ema(df, window)
    return df['close'] > ema

def is_trending_down(df: pd.DataFrame, window: int = 50) -> pd.Series:
    """
    Detect downtrend by checking if close price is below EMA.
    Returns a boolean pd.Series indicating downtrend periods.
    """
    ema = get_ema(df, window)
    return df['close'] < ema

def is_volatile(df: pd.DataFrame, window: int = 14, threshold: float = 1.5) -> pd.Series:
    """
    Identify high volatility periods using ATR compared to its SMA.
    Returns a boolean pd.Series where ATR exceeds its SMA multiplied by threshold.
    """
    atr = ta.atr(high=df['high'], low=df['low'], close=df['close'], length=window)
    atr_sma = ta.sma(atr, length=window)
    return atr > atr_sma * threshold

def volume_spike(df: pd.DataFrame, window: int = 20, threshold: float = 2.0) -> pd.Series:
    """
    Detect volume spikes where current volume exceeds its SMA multiplied by threshold.
    Returns a boolean pd.Series indicating volume spike periods.
    """
    vol_sma = ta.sma(df['volume'], length=window)
    return df['volume'] > vol_sma * threshold

if __name__ == "__main__":
    print("GP Blocks library loaded.")

# Example usage:
# buy_signal = and_op(
#     is_trending_up(df, 50),
#     cross_up(get_rsi(df, 14), 30)
# )
