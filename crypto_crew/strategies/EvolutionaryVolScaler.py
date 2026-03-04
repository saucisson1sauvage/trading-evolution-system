import numpy as np
import pandas as pd
from pandas import DataFrame
from typing import Optional, Union
from functools import reduce
import os
import json
import math

from freqtrade.strategy import (
    IStrategy, informative, IntParameter, DecimalParameter, BooleanParameter, CategoricalParameter
)
import talib.abstract as ta
from technical import qtpylib

class EvolutionaryVolScaler(IStrategy):
    """
    EvolutionaryVolScaler v8 - ANALYTICAL OMNIBUS
    Expanded feedback dimensions for the AI loop.
    """
    INTERFACE_VERSION = 3
    timeframe = '1m'
    informative_timeframe = '1h'

    # --- STRUCTURAL DNA ---
    long_logic = CategoricalParameter(['trend_follower', 'mean_reversion', 'quick_scalp', 'vol_breakout'], default='trend_follower', space="buy")
    short_logic = CategoricalParameter(['vortex_short', 'ema_rejection', 'exhaustion_short', 'none'], default='none', space="buy")
    exit_logic = CategoricalParameter(['rsi_extreme', 'trailing_profit', 'volatility_exit', 'none'], default='rsi_extreme', space="sell")
    
    # --- DYNAMIC PARAMETERS ---
    buy_rsi = IntParameter(10, 45, default=30, space="buy")
    short_rsi = IntParameter(55, 90, default=70, space="buy")
    buy_adx = IntParameter(20, 50, default=25, space="buy")
    sell_rsi_long = IntParameter(70, 95, default=80, space="sell")
    sell_rsi_short = IntParameter(5, 30, default=20, space="sell")

    # Protections
    stoploss = -0.03
    minimal_roi = {"0": 0.02, "10": 0.01, "30": 0}
    trailing_stop = True
    can_short = True

    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        h_window = 24
        h_wma_half = dataframe['close'].rolling(window=h_window//2).mean()
        h_wma_full = dataframe['close'].rolling(window=h_window).mean()
        h_diff = 2 * h_wma_half - h_wma_full
        dataframe['hma'] = h_diff.rolling(window=int(np.sqrt(h_window))).mean()
        return dataframe

    @informative('5m')
    def populate_indicators_5m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['ema8'] = ta.EMA(dataframe, timeperiod=8)
        dataframe['ema21'] = ta.EMA(dataframe, timeperiod=21)
        keltner = qtpylib.keltner_channel(dataframe, window=20, atrs=2)
        dataframe['kelt_u'] = keltner['upper']
        dataframe['kelt_l'] = keltner['lower']
        dataframe['dist_ema'] = (dataframe['close'] - dataframe['ema21']) / dataframe['ema21']
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)

        # AI Vibe Path update
        vibe_file = "/home/saus/crypto_crew/market_vibe.json"
        self.ai_vibe = 0.0
        try:
            if os.path.exists(vibe_file):
                with open(vibe_file, 'r') as f:
                    self.ai_vibe = json.load(f).get('vibe_score', 0.0)
        except: pass

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cond_l = []
        cond_s = []
        if self.long_logic.value == 'trend_follower':
            cond_l.append(dataframe['ema8'] > dataframe['ema21'])
            cond_l.append(dataframe['adx'] > self.buy_adx.value)
        elif self.long_logic.value == 'mean_reversion':
            cond_l.append(dataframe['rsi'] < self.buy_rsi.value)
            cond_l.append(dataframe['close'] < dataframe['ema50_5m'])
        elif self.long_logic.value == 'quick_scalp':
            cond_l.append(dataframe['close'] > dataframe['ema8']) 
            cond_l.append(dataframe['rsi_5m'] < 35)
        elif self.long_logic.value == 'vol_breakout':
            cond_l.append(dataframe['close'] > dataframe['kelt_u'])

        if self.short_logic.value == 'vortex_short':
            cond_s.append(dataframe['dist_ema'] > 0.015)
            cond_s.append(dataframe['rsi'] > self.short_rsi.value)
        elif self.short_logic.value == 'ema_rejection':
            cond_s.append(dataframe['close'] < dataframe['ema21'])
            cond_s.append(dataframe['high'] > dataframe['ema21'])
        elif self.short_logic.value == 'exhaustion_short':
            cond_s.append(dataframe['rsi'] > 80)
            cond_s.append(dataframe['volume'] > ta.EMA(dataframe['volume'], 20) * 1.8)

        if cond_l:
            from functools import reduce
            dataframe.loc[reduce(lambda x, y: x & y, cond_l) & (dataframe['volume'] > 0), 'enter_long'] = 1
        if cond_s:
            from functools import reduce
            dataframe.loc[reduce(lambda x, y: x & y, cond_s) & (dataframe['volume'] > 0), 'enter_short'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.exit_logic.value == 'rsi_extreme':
            dataframe.loc[(dataframe['rsi'] > self.sell_rsi_long.value), 'exit_long'] = 1
            dataframe.loc[(dataframe['rsi'] < self.sell_rsi_short.value), 'exit_short'] = 1
        elif self.exit_logic.value == 'volatility_exit':
            dataframe.loc[(dataframe['close'] > dataframe['kelt_u']), 'exit_long'] = 1
            dataframe.loc[(dataframe['close'] < dataframe['kelt_l']), 'exit_short'] = 1
        return dataframe
