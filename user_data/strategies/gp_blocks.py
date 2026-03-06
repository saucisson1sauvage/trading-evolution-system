import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Union, Tuple, Callable, Dict, Any

# Universal Block Registry
BLOCK_REGISTRY: Dict[str, Dict[str, Callable]] = {
    'num': {},
    'bool_helper': {},
    'comparator': {},
    'operator': {}
}

def register_block(category: str, name: str):
    """Decorator to register a function into the BLOCK_REGISTRY."""
    def decorator(func):
        if category not in BLOCK_REGISTRY:
            raise ValueError(f"Invalid block category: {category}")
        BLOCK_REGISTRY[category][name] = func
        return func
    return decorator

# --- BASE METRICS ---
@register_block('num', 'OPEN')
def get_open(df: pd.DataFrame, **kwargs) -> pd.Series:
    return df['open']

@register_block('num', 'HIGH')
def get_high(df: pd.DataFrame, **kwargs) -> pd.Series:
    return df['high']

@register_block('num', 'LOW')
def get_low(df: pd.DataFrame, **kwargs) -> pd.Series:
    return df['low']

@register_block('num', 'CLOSE')
def get_close(df: pd.DataFrame, **kwargs) -> pd.Series:
    return df['close']

@register_block('num', 'VOLUME')
def get_volume(df: pd.DataFrame, **kwargs) -> pd.Series:
    return df['volume']

# --- NUM INDICATORS ---
@register_block('num', 'RSI')
def get_rsi(df: pd.DataFrame, window: int = 14, **kwargs) -> pd.Series:
    return ta.rsi(close=df['close'], length=window)

@register_block('num', 'EMA')
def get_ema(df: pd.DataFrame, window: int, **kwargs) -> pd.Series:
    return ta.ema(close=df['close'], length=window)

@register_block('num', 'SMA')
def get_sma(df: pd.DataFrame, window: int, **kwargs) -> pd.Series:
    return ta.sma(close=df['close'], length=window)

def get_bollinger(df: pd.DataFrame, window: int = 20, std: float = 2.0, **kwargs) -> Tuple[pd.Series, pd.Series, pd.Series]:
    bb = ta.bbands(close=df['close'], length=window, std=std)
    return bb[f'BBU_{window}_{std}'], bb[f'BBM_{window}_{std}'], bb[f'BBL_{window}_{std}']

@register_block('num', 'BB_UPPER')
def get_bb_upper(df: pd.DataFrame, window: int = 20, std: float = 2.0, **kwargs) -> pd.Series:
    u, m, l = get_bollinger(df, window, std)
    return u

@register_block('num', 'BB_MIDDLE')
def get_bb_middle(df: pd.DataFrame, window: int = 20, std: float = 2.0, **kwargs) -> pd.Series:
    u, m, l = get_bollinger(df, window, std)
    return m

@register_block('num', 'BB_LOWER')
def get_bb_lower(df: pd.DataFrame, window: int = 20, std: float = 2.0, **kwargs) -> pd.Series:
    u, m, l = get_bollinger(df, window, std)
    return l

# --- COMPARATORS ---
@register_block('comparator', 'GREATER_THAN')
def greater_than(s1: pd.Series, s2: Union[pd.Series, float, int], **kwargs) -> pd.Series:
    return s1 > s2

@register_block('comparator', 'LESS_THAN')
def less_than(s1: pd.Series, s2: Union[pd.Series, float, int], **kwargs) -> pd.Series:
    return s1 < s2

@register_block('comparator', 'CROSS_UP')
def cross_up(s1: pd.Series, threshold: Union[pd.Series, float, int], **kwargs) -> pd.Series:
    return (s1.shift(1) <= threshold) & (s1 > threshold)

@register_block('comparator', 'CROSS_DOWN')
def cross_down(s1: pd.Series, threshold: Union[pd.Series, float, int], **kwargs) -> pd.Series:
    return (s1.shift(1) >= threshold) & (s1 < threshold)

# --- OPERATORS ---
@register_block('operator', 'AND')
def and_op(b1: pd.Series, b2: pd.Series, **kwargs) -> pd.Series:
    return b1 & b2

@register_block('operator', 'OR')
def or_op(b1: pd.Series, b2: pd.Series, **kwargs) -> pd.Series:
    return b1 | b2

@register_block('operator', 'NOT')
def not_op(b: pd.Series, **kwargs) -> pd.Series:
    return ~b

# --- BOOL HELPERS ---
@register_block('bool_helper', 'TRENDING_UP')
def is_trending_up(df: pd.DataFrame, window: int = 50, **kwargs) -> pd.Series:
    ema = get_ema(df, window)
    return df['close'] > ema

@register_block('bool_helper', 'TRENDING_DOWN')
def is_trending_down(df: pd.DataFrame, window: int = 50, **kwargs) -> pd.Series:
    ema = get_ema(df, window)
    return df['close'] < ema

@register_block('bool_helper', 'VOLATILE')
def is_volatile(df: pd.DataFrame, window: int = 14, threshold: float = 1.5, **kwargs) -> pd.Series:
    atr = ta.atr(high=df['high'], low=df['low'], close=df['close'], length=window)
    atr_sma = ta.sma(atr, length=window)
    return atr > atr_sma * threshold

@register_block('bool_helper', 'VOLUME_SPIKE')
def volume_spike(df: pd.DataFrame, window: int = 20, threshold: float = 2.0, **kwargs) -> pd.Series:
    vol_sma = ta.sma(df['volume'], length=window)
    return df['volume'] > vol_sma * threshold

if __name__ == "__main__":
    print("GP Blocks library loaded.")
    print("Registered Blocks:", BLOCK_REGISTRY)
