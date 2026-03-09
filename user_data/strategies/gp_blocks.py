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

def register_block(category: str, name: str, description: str = ""):
    """Decorator to register a function into the BLOCK_REGISTRY with a description."""
    def decorator(func):
        if category not in BLOCK_REGISTRY:
            raise ValueError(f"Invalid block category: {category}")
        # Attach description as an attribute to the function
        func.description = description
        BLOCK_REGISTRY[category][name] = func  # Registry remains just callables
        return func
    return decorator

# --- BASE METRICS ---
@register_block('num', 'OPEN', "Returns the opening price of the current candle.")
def get_open(df: pd.DataFrame, **kwargs) -> pd.Series:
    return df['open']

@register_block('num', 'HIGH', "Returns the highest price of the current candle. Used for breakout thresholds.")
def get_high(df: pd.DataFrame, **kwargs) -> pd.Series:
    return df['high']

@register_block('num', 'LOW', "Returns the lowest price of the current candle. Used for invalidation levels.")
def get_low(df: pd.DataFrame, **kwargs) -> pd.Series:
    return df['low']

@register_block('num', 'CLOSE', "Returns the closing price of the current candle. The standard baseline for price action.")
def get_close(df: pd.DataFrame, **kwargs) -> pd.Series:
    return df['close']

@register_block('num', 'VOLUME', "Returns the trading volume. Essential for liquidity and institutional flow validation.")
def get_volume(df: pd.DataFrame, **kwargs) -> pd.Series:
    return df['volume']

# --- NUM INDICATORS ---
@register_block('num', 'RSI', "Relative Strength Index (0-100). Measures momentum. <30 is oversold, >70 is overbought. Requires 'window' parameter.")
def get_rsi(df: pd.DataFrame, window: int = 14, **kwargs) -> pd.Series:
    return ta.rsi(close=df['close'], length=window)

@register_block('num', 'EMA', "Exponential Moving Average. Reacts quickly to recent price changes. Good for fast trends. Requires 'window' parameter.")
def get_ema(df: pd.DataFrame, window: int, **kwargs) -> pd.Series:
    return ta.ema(close=df['close'], length=window)

@register_block('num', 'SMA', "Simple Moving Average. Smoother, slower trend indicator. Good for macro baselines. Requires 'window' parameter.")
def get_sma(df: pd.DataFrame, window: int, **kwargs) -> pd.Series:
    return ta.sma(close=df['close'], length=window)

def get_bollinger(df: pd.DataFrame, window: int = 20, std: float = 2.0, **kwargs) -> Tuple[pd.Series, pd.Series, pd.Series]:
    bb = ta.bbands(close=df['close'], length=window, std=std)
    return bb[f'BBU_{window}_{std}'], bb[f'BBM_{window}_{std}'], bb[f'BBL_{window}_{std}']

@register_block('num', 'BB_UPPER', "Bollinger Bands Upper Band. Represents +N standard deviations. Hits indicate overextended upside volatility. Requires 'window' and 'std'.")
def get_bb_upper(df: pd.DataFrame, window: int = 20, std: float = 2.0, **kwargs) -> pd.Series:
    u, m, l = get_bollinger(df, window, std)
    return u

@register_block('num', 'BB_MIDDLE', "Bollinger Bands Middle Band (SMA). Baseline for mean reversion. Requires 'window' and 'std'.")
def get_bb_middle(df: pd.DataFrame, window: int = 20, std: float = 2.0, **kwargs) -> pd.Series:
    u, m, l = get_bollinger(df, window, std)
    return m

@register_block('num', 'BB_LOWER', "Bollinger Bands Lower Band. Represents -N standard deviations. Hits indicate oversold capitulation. Requires 'window' and 'std'.")
def get_bb_lower(df: pd.DataFrame, window: int = 20, std: float = 2.0, **kwargs) -> pd.Series:
    u, m, l = get_bollinger(df, window, std)
    return l

# --- COMPARATORS ---
@register_block('comparator', 'GREATER_THAN', "Returns True if the 'left' node evaluates strictly greater than the 'right' node.")
def greater_than(s1: pd.Series, s2: Union[pd.Series, float, int], **kwargs) -> pd.Series:
    return s1 > s2

@register_block('comparator', 'LESS_THAN', "Returns True if the 'left' node evaluates strictly less than the 'right' node.")
def less_than(s1: pd.Series, s2: Union[pd.Series, float, int], **kwargs) -> pd.Series:
    return s1 < s2

@register_block('comparator', 'CROSS_UP', "Returns True ONLY if the 'left' node crossed ABOVE the 'right' node on this exact candle. Powerful trigger signal.")
def cross_up(s1: pd.Series, threshold: Union[pd.Series, float, int], **kwargs) -> pd.Series:
    return (s1.shift(1) <= threshold) & (s1 > threshold)

@register_block('comparator', 'CROSS_DOWN', "Returns True ONLY if the 'left' node crossed BELOW the 'right' node on this exact candle. Powerful exit/short signal.")
def cross_down(s1: pd.Series, threshold: Union[pd.Series, float, int], **kwargs) -> pd.Series:
    return (s1.shift(1) >= threshold) & (s1 < threshold)

# --- OPERATORS ---
@register_block('operator', 'AND', "Logical AND. True only if all child nodes in the list evaluate to True. Used for strict condition gating (e.g., Signal AND Trend).")
def and_op(b1: pd.Series, b2: pd.Series, **kwargs) -> pd.Series:
    return b1 & b2

@register_block('operator', 'OR', "Logical OR. True if at least one child node evaluates to True. Used for flexible exit conditions.")
def or_op(b1: pd.Series, b2: pd.Series, **kwargs) -> pd.Series:
    return b1 | b2

@register_block('operator', 'NOT', "Logical NOT. Inverts the boolean value of its child node. E.g., NOT(VOLATILE) ensures a calm market environment.")
def not_op(b: pd.Series, **kwargs) -> pd.Series:
    return ~b

# --- BOOL HELPERS ---
@register_block('bool_helper', 'TRENDING_UP', "Returns True if the asset is in a structural uptrend (e.g. price > SMA). High windows (50+) indicate macro safety. Requires 'window'.")
def is_trending_up(df: pd.DataFrame, window: int = 50, **kwargs) -> pd.Series:
    ema = get_ema(df, window)
    return df['close'] > ema

@register_block('bool_helper', 'TRENDING_DOWN', "Returns True if the asset is in a structural downtrend. Requires 'window'.")
def is_trending_down(df: pd.DataFrame, window: int = 50, **kwargs) -> pd.Series:
    ema = get_ema(df, window)
    return df['close'] < ema

@register_block('bool_helper', 'VOLATILE', "Returns True if current volatility (ATR or BB width) exceeds the historical baseline. Crucial for breakout timing. Requires 'window' and 'threshold'.")
def is_volatile(df: pd.DataFrame, window: int = 14, threshold: float = 1.5, **kwargs) -> pd.Series:
    atr = ta.atr(high=df['high'], low=df['low'], close=df['close'], length=window)
    atr_sma = ta.sma(atr, length=window)
    return atr > atr_sma * threshold

@register_block('bool_helper', 'VOLUME_SPIKE', "Returns True if current volume is > threshold * SMA(volume). Validates institutional order flow and trade toxicity. Requires 'window' and 'threshold'.")
def volume_spike(df: pd.DataFrame, window: int = 20, threshold: float = 2.0, **kwargs) -> pd.Series:
    vol_sma = ta.sma(df['volume'], length=window)
    return df['volume'] > vol_sma * threshold

if __name__ == "__main__":
    print("GP Blocks library loaded.")
    print("Registered Blocks:", BLOCK_REGISTRY)
