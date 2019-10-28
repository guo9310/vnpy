"""命令行下单策略"""
import datetime
import inspect
import shlex
import time

from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
)
from vnpy.app.cta_strategy.base import StopOrderStatus
from vnpy.event import EVENT_TIMER, Event
from vnpy.trader.constant import (Direction, Offset, Status)
from vnpy.trader.event import EVENT_COMMAND, EVENT_COMMAND_MSG


class CommandOrderStrategy(CtaTemplate):
    author = "Yonggang Guo"

    parameters = []
    variables = []

    # 最新Tick
    last_tick = None
    # 止盈单ID <-> 止损单ID(本地停止单), 用于配对一方成交后取消另一方
    order_pair = None

    # 止盈止损等设置, 从cta_engine读取
    setting = None

    # 命令下单的委托单ID列表
    command_orderids = None

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """命令行下单策略"""
        super(CommandOrderStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, setting
        )

        self.last_tick = None
        self.order_pair = {}

        self.cta_engine.event_engine.register(EVENT_TIMER, self.on_timer)
        self.cta_engine.event_engine.register(EVENT_COMMAND, self.on_command_event)

        self.command_orderids = []

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        # 加载参数配置
        self.setting = self.cta_engine.strategy_setting[self.strategy_name]['setting']

        self.write_log("命令行下单策略初始化")
        self.put_event()

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("命令行下单策略启动")
        self.put_event()

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")
        self.put_event()

    def on_timer(self, event):
        """timer"""
        pass

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.last_tick = tick
        self.put_event()

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        if stop_order.status == StopOrderStatus.TRIGGERED:
            # 停止单被触发后, 要取消对应的止盈单
            if stop_order.stop_orderid in self.order_pair:
                pair_id = self.order_pair[stop_order.stop_orderid]
                self.cancel_order(pair_id)

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.check_order_condition(trade)

    def check_order_condition(self, trade: TradeData):
        if trade.vt_orderid in self.command_orderids:
            # 命令单成交后, 要自动生成两单：1. 止盈单; 2. 本地停止单, 止损
            position_holding = self.cta_engine.offset_converter.get_position_holding(trade.vt_symbol)
            pos = position_holding.long_pos - position_holding.short_pos
            # 判断是否有一手敞口的多单/空单
            if pos != 0:
                return

            if (trade.direction is Direction.LONG and pos > 0) or (trade.direction is Direction.SHORT and pos < 0):
                self.stop_win_lose(trade)
        else:
            # 止盈止损单
            if trade.vt_orderid in self.order_pair:
                pair_id = self.order_pair[trade.vt_orderid]
                self.cancel_order(pair_id)

    def stop_win_lose(self, trade):
        if trade.direction is Direction.LONG:
            id1 = self.sell(trade.price + self.setting['win'], 1, stop=False, lock=True)
            id2 = self.sell(trade.price - self.setting['lose'], 1, stop=True, lock=True)
        else:
            id1 = self.cover(trade.price - self.setting['win'], 1, stop=False, lock=True)
            id2 = self.cover(trade.price + self.setting['lose'], 1, stop=True, lock=True)
        self.order_pair[id1[0]] = id2[0]
        self.order_pair[id2[0]] = id1[0]

    def on_command_event(self, event: Event):
        if event.data.vt_symbol == self.vt_symbol:
            self.do_command(event.data.command)

    def do_command(self, args: str):
        self.write_log(f'收到命令: {args}')
        ops: list = shlex.split(args)
        op: str = ops[0]
        if op == 'long':
            self.command_long()
        else:
            self.write_log(f"没有此下单命令: {op}")

    def command_long(self):
        order_ids = self.buy(self.last_tick.ask_price_1, 1, lock=True)
        self.command_orderids.extend(order_ids)
