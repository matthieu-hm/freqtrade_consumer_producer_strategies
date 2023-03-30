import copy
import logging
import pathlib
import rapidjson
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import talib.abstract as ta
import pandas as pd
import pandas_ta as pta
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import merge_informative_pair
from pandas import DataFrame, Series
from functools import reduce, partial
from freqtrade.persistence import Trade, LocalTrade
from datetime import datetime, timedelta
import time
from typing import Optional
import warnings

log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

class ProducerConsumerStrategy(IStrategy):
    INTERFACE_VERSION: int = 3


    #############################################################
    # Strategy parameters -->

    # ROI table:
    minimal_roi = {
        "0": 100.0,
    }

    stoploss = -0.99

    # Trailing stoploss (not used)
    trailing_stop = False
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03

    use_custom_stoploss = False

    timeframe = '5m'

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    # <-- Strategy parameters
    #############################################################


    #############################################################
    # Producers / Consumer
    is_consumer = False
    process_only_new_candles = True


    def __init__(self, config: dict) -> None:
        super().__init__(config)

        if ('external_message_consumer' in self.config and 'producers' in self.config['external_message_consumer']
                and len(self.config['external_message_consumer']['producers']) > 0):
            self.is_consumer = True
            self.process_only_new_candles = False  # required for consumers


    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.is_consumer:
            producer_dataframe = self.populate_indicators_from_producers(dataframe, metadata)
            return producer_dataframe

        # ... (strategy logic)
        return dataframe


    def populate_indicators_from_producers(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']

        for producer in self.config['external_message_consumer']['producers']:
            if (producer.name):
                # This func returns the analyzed dataframe, and when it was analyzed
                producer_dataframe, _ = self.dp.get_producer_df(pair, producer_name=producer.name)

                if not producer_dataframe.empty:
                    log.debug(f"[{metadata['pair']}] Populate indicators from producer {producer['name']}")
                    return producer_dataframe

        # No dataframe provided by any producer: minimal dataframe fallback
        # FIXME: Define default value for all indicators
        #        -> When starting with active trade, stategie callbacks that use indicators
        #           are going to throw errors
        required_columns = ['enter_long', 'enter_short', 'exit_long', 'exit_short']
        dataframe[required_columns] = 0
        log.debug(f"[{metadata['pair']}] No indicators found from producers")
        return dataframe


    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.is_consumer:
            # Dataframe from populate_indicators_from_producers
            # -> indicators already populated
            # TODO: Needs to be confirmed
            return dataframe

        # ... (strategy logic)
        return dataframe


    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.is_consumer:
            # Dataframe from populate_indicators_from_producers
            # -> indicators already populated
            # TODO: Needs to be confirmed
            return dataframe

        # ... (strategy logic)
        return dataframe
