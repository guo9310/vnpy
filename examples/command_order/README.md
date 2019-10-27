# 命令行下单工具
* 现在的交易软件都是图形界面的，使用鼠标和数字键盘就可以方便的进行交易了
* 但使用图形界面是很容易出错：点的太快, 或焦点问题导致数字输入错误等等
* 所以我们开发一个命令行下单工具，模拟Linux的终端，输入特定的命令，进行交易
* 命令行下单工具的主要功能:
  - 可以进行做多和做空操作
  - 在交易成功后，根据配置来生成止盈止损单
  - 在价格符合的条件下，自动进行止盈止损，并可以接收到成交回报

## 命令说明

* 进入Shell之后, 可以看到提示符：IC1911>， 说明当前操作的期货合约


* 输入help，查看命令列表

* 输入help command，查看某个命令的详细说明

* 支持命令补全
    - 输入命令前面的字符, 按一下Tab键，如果前缀对应只有一个命令，直接补全
    - 如果有多个同样前缀的命令，按两下Tab键，可以列出候选命令
    - 也可以直接按两次Tab，列出所有命令


## 目前已经实现的命令
只有long/help/exit

        
## 命令列表

* 日常操盘命令(根据昨仓/今仓情况进行开仓/平仓/锁仓操作)
1. long:   做多
2. short:  做空


* 更改状态命令
1. cancel: 取消所有未成交的委托单, 包括本地停止单
2. code: 如code IC1906，切换当前操作的股指期货代码


* 查看状态命令
1. order: 当前委托单列表, 包括本地停止单
2. trade: 成交列表
3. position: 当前持仓
4. account: 账户情况


* 帮助命令
1. help: 帮助
2. exit: 退出, 也可以用Ctrl+c退出


## 做多命令的流程
* 例如： IC1911 
    - long做多，挂单价是取卖1价, 最终成交价是5000
    - 那么会自动生成一个止盈单5003
    - 还有一个止损单（本地停止单/条件单), 4997
    - 如果止盈单5003成交，会撤销对应的止损单
    - 如果止损单4997符合条件了，就触发实际止损单, 并撤销对应的止盈单5003
    - 注意：实际止损单的挂单价格(股指期货IC/IF/IH是有涨跌停限制的)
        - 如果合约有涨跌停限制，那么价格是今日涨跌停价
        - 如果没有涨跌停限制，就取对手价第5档（买5或卖5）

## 使用流程

### 策略配置文件
order_tools/examples/command_order/.vntrader/cta_strategy_setting.json
* 可以有多个策略同时运行，比如：三个股指期货(IC/IF/IH), class_name可以一样。
* setting：
    - win  止盈点
    - lose 止损点

```json
{
  "IC": {
    "class_name": "CommandOrderStrategy",
    "vt_symbol": "IC1911.CFFEX",
    "setting": {
      "win": 3,
      "lose": 3
    }
  }
}
```

### 修改simnow的账号密码
order_tools/examples/command_order/run_server.py

把其中的simnow账号和密码改成自己的

### 启动服务器
```bash
set PYTHONPATH=/home/username/order_tools/
cd order_tools/examples/command_order
python run_server.py
```
### 启动客户端
```bash
set PYTHONPATH=/home/username/order_tools/
cd order_tools/examples/command_order
python run_terminal.py IC1911
```

