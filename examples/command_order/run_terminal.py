import os
import sys
from cmd import Cmd
from enum import Enum

from terminaltables import AsciiTable

from vnpy.app.rpc_service.engine import EVENT_RPC_LOG
from vnpy.event import EventEngine, Event
from vnpy.gateway.rpc import RpcGateway
from vnpy.trader.constant import Exchange
from vnpy.trader.engine import MainEngine
from vnpy.trader.event import EVENT_LOG, EVENT_COMMAND, EVENT_COMMAND_MSG, EVENT_TRADE, EVENT_TICK
from vnpy.trader.object import CommandRequest
from vnpy.trader.utility import load_json


class Terminal(Cmd):
    rpc_setting = {
        "主动请求地址": "tcp://127.0.0.1:2019",
        "推送订阅地址": "tcp://127.0.0.1:9102"
    }
    setting_filename = "rpc_service_setting.json"
    prompt = 'cot> '
    intro = '欢迎进入命令下单工具!'

    def __init__(self, code):
        Cmd.__init__(self)
        self.code = code
        self.prompt = self.code + '> '

        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)

        self.main_engine.add_gateway(RpcGateway)

        self.oms_engine = self.main_engine.get_engine("oms")
        self.log_engine = self.main_engine.get_engine("log")
        self.event_engine.register(EVENT_LOG, self.log_engine.process_log_event)
        self.event_engine.register(EVENT_RPC_LOG, self.log_engine.process_log_event)

        self.event_engine.register(EVENT_TRADE, self.process_trade_event)
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_COMMAND_MSG, self.process_msg_event)

        self.load_rpc_setting()
        self.rpcGateway = self.main_engine.get_gateway("RPC")
        self.rpcGateway.connect(self.rpc_setting)

        self.last_tick = None

    def load_rpc_setting(self):
        setting = load_json(self.setting_filename)
        if 'rep_address' in setting:
            self.rpc_setting['主动请求地址'] = setting['rep_address']
        if 'pub_address' in setting:
            self.rpc_setting['推送订阅地址'] = setting['pub_address']

    def process_trade_event(self, event: Event):
        trade = event.data
        if self.code == trade.symbol:
            print(f'\x1b[0;31;44m成交事件\x1b[0m')
            self.obj2table([trade])
            self.stdout.write(self.prompt)
            self.stdout.flush()

    def process_tick_event(self, event: Event):
        tick = event.data
        if self.code == tick.symbol:
            self.last_tick = tick

    def process_msg_event(self, event: Event):
        print(event.data)
        self.stdout.write(self.prompt)
        self.stdout.flush()

    def send_command(self, command: str):
        req = CommandRequest(self.code, Exchange.CFFEX, command)
        event = Event(EVENT_COMMAND, req)
        self.rpcGateway.client.put(event)

    def do_long(self, arg):
        """long: 做多"""
        self.send_command('long')

    def do_order(self, arg):
        """所有订单列表"""
        orders = self.oms_engine.get_all_orders()
        self.obj2table(orders, '委托单')

        stop_orders = self.rpcGateway.client.get_all_stop_orders().values()
        self.obj2table(list(stop_orders), '本地停止单')

    def do_exit(self, arg):
        """退出"""
        sys.exit(0)

    def default(self, line):
        print("未知命令! 请使用help来查看命令列表 ")

    def emptyline(self):
        pass

    @staticmethod
    def obj2table(obj_list, title=None):
        def print_value(field):
            if isinstance(field, Enum):
                return field.value
            elif isinstance(field, float):
                return round(field, 2)
            return field

        if len(obj_list) > 0:
            rows = []
            headers = obj_list[0].__dict__.keys()
            rows.append(headers)

            for o in obj_list:
                row = [print_value(o.__dict__[key]) for key in headers]
                rows.append(row)

            t = AsciiTable(rows, title)
            print(t.table)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(u"请输入要操作的期货合约, 如: python run_terminal.py IC1911")
        sys.exit()
    try:
        cls = 'clear'
        if 'win32' in sys.platform:
            cls = 'cls'
        os.system(cls)
        term = Terminal(sys.argv[1])
        term.cmdloop()
    except Exception as e:
        print(e)
        sys.exit()
