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

class DummyConsumerStrategy(IStrategy):
    INTERFACE_VERSION: int = 3


    #############################################################
    # Strategy parameters -->

    timeframe = '5m'

    stoploss = -0.05

    # <-- Strategy parameters
    #############################################################


    #############################################################
    # Producers / Consumer

    is_consumer = False

    process_only_new_candles = True


    def __init__(self, config: dict) -> None:
        super().__init__(config)

        if ('external_message_consumer' in self.config and 'producers' in self.config['external_message_consumer']
                and self.config['external_message_consumer']['enabled']
                and len(self.config['external_message_consumer']['producers']) > 0):
            self.is_consumer = True
            self.process_only_new_candles = False  # required for consumers


    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.is_consumer:
            return self.get_dataframe_from_producers(dataframe, metadata['pair'])

        # ... (strategy logic)
        return dataframe


    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.is_consumer:
            # Dataframe already analysed
            return dataframe

        # ... (strategy logic)
        return dataframe


    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.is_consumer:
            # Dataframe already analysed
            return dataframe

        # ... (strategy logic)
        return dataframe


    # OPTIONAL: If the strategy uses other callbacks that require the dataframe
    #           check if the dataframe is available before (for the consumer)


    # # OPTIONAL: If the strategy uses this callback
    # def adjust_trade_position(self, trade: Trade, current_time: datetime,
    #                       current_rate: float, current_profit: float,
    #                       min_stake: Optional[float], max_stake: float,
    #                       current_entry_rate: float, current_exit_rate: float,
    #                       current_entry_profit: float, current_exit_profit: float,
    #                       **kwargs) -> Optional[float]:
    #     if (self.position_adjustment_enable == False):
    #         return None

    #     if (self.is_consumer and not self.has_access_to_dataframe_from_producers(trade.pair)):
    #         # Consumer started before the producer that handles this pair and has active trades
    #         # No data available yet, do nothing
    #         return None

    #     # ... (strategy logic)
    #     return None


    # # OPTIONAL: If the strategy uses this callback
    # def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float,
    #                 current_profit: float, **kwargs):
    #     if (self.is_consumer and not self.has_access_to_dataframe_from_producers(pair)):
    #         # Consumer started before the producer that handles this pair and has active trades
    #         # No data available yet, do nothing
    #         return None

    #     # ... (strategy logic)
    #     return None


# +---------------------------------------------------------------------------+
# |                              Consumer                                     |
# +---------------------------------------------------------------------------+

    def get_dataframe_from_producers(self, dataframe: DataFrame, pair: str) -> DataFrame:
        for producer in self.config['external_message_consumer']['producers']:
            if (producer['name']):
                # This func returns the analyzed dataframe, and when it was analyzed
                producer_dataframe, _ = self.dp.get_producer_df(pair, producer_name=producer['name'])

                if not producer_dataframe.empty:
                    log.debug(f"[{pair}] Get dataframe from producer \"{producer['name']}\"")

                    merged_dataframe = merge_informative_pair(dataframe, producer_dataframe,
                                                      self.timeframe, self.timeframe,
                                                      ffill=True,
                                                      append_timeframe=False)

                    # The function merge_informative_pair() adds suffixes to the requiered columns
                    # ('date', 'open', 'high', 'low', 'close', 'volume')
                    # origin dataframe columns: _x
                    # producer_dataframe columns: _y

                    # -> We keep only the columns from the consumer dataframe (origin),
                    #    as the consumer update the values more often than the producers

                    # Get all merged_dataframe columns ending with _x
                    merged_dataframe_columns_x = [col for col in merged_dataframe.columns if col.endswith('_x')]
                    # Remove suffix "_x" from merged_dataframe columns
                    merged_dataframe.rename(columns=dict(zip(merged_dataframe_columns_x, [col[:-2] for col in merged_dataframe_columns_x])), inplace=True)

                    return merged_dataframe

        # No dataframe provided by any producer: minimal dataframe fallback
        required_columns_default_0 = ['enter_long', 'enter_short', 'exit_long', 'exit_short']
        required_columns_default_none = ['enter_tag','exit_tag']

        dataframe[required_columns_default_0] = 0
        dataframe[required_columns_default_none] = None
        log.debug(f"[{pair}] No dataframe found from producers")
        return dataframe


    def has_access_to_dataframe_from_producers(self, pair: str) -> bool:
        for producer in self.config['external_message_consumer']['producers']:
            if (producer['name']):
                # This func returns the analyzed dataframe, and when it was analyzed
                producer_dataframe, _ = self.dp.get_producer_df(pair, producer_name=producer['name'])

                if not producer_dataframe.empty:
                    log.debug(f"[{pair}] Found dataframe: producer \"{producer['name']}\"")
                    return True

        log.debug(f"[{pair}] No dataframe found from producers")
        return False
