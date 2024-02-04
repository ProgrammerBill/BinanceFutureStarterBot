import time
from binance.client import Client
from binance.enums import *
import configparser
import argparse
from strategy.futures_bot_strategy import BasicBotStrategy
import prettyprinter
from datetime import datetime


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def pprint_with_timestamp(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{bcolors.HEADER}[{timestamp}]:{bcolors.ENDC} {message}")


parser = argparse.ArgumentParser()
parser.add_argument("-t", action="store_true", help="for testnet")
args = parser.parse_args()

config = configparser.ConfigParser()
# reading config file
config.read("user.cfg")
symbol = config.get("binance_user_config", "symbol")
quantity = float(config.get("binance_user_config", "quantity"))
target_profit_usdt = float(config.get("binance_user_config", "target_profit_usdt"))
target_loss_usdt = float(config.get("binance_user_config", "target_loss_usdt"))

# use testnet api_key pair for debug
if args.t:
    api_key = config.get("binance_user_config", "test_api_key")
    api_secret = config.get("binance_user_config", "test_api_secret")
    client = Client(api_key, api_secret, testnet=True, requests_params={"timeout": 50})
else:
    api_key = config.get("binance_user_config", "api_key")
    api_secret = config.get("binance_user_config", "api_secret")
    client = Client(api_key, api_secret, requests_params={"timeout": 50})

# 使用BasicBotStrategy
strategy = BasicBotStrategy(client, symbol)

# get the current price for the symbol
prices = client.get_symbol_ticker(symbol=symbol)
current_price = float(prices["price"])
notional = quantity * current_price
min_notional = 0

# 获取交易对信息
info = client.get_exchange_info()

# 在交易对信息中查找特定symbol的信息
for symbol_info in info["symbols"]:
    if symbol_info["symbol"] == symbol:
        for filter in symbol_info["filters"]:
            if filter["filterType"] == "NOTIONAL":
                min_notional = float(filter["minNotional"])
                #print("min_notional:", min_notional)
                break

#print("notional:", notional)
if notional < min_notional:
    quantity = min_notional / current_price
    quantity = round(quantity, 2)
    #print("fixed notional:", quantity * current_price)

leverage = config.get("binance_user_config", "leverage")
response = client.futures_change_leverage(symbol=symbol, leverage=leverage)
#print(response)

# position_mode = client.futures_get_position_mode()
# print("当前持仓模式:", "双向" if position_mode["dualSidePosition"] else "单向")
# 切换到对冲模式
# response = client.futures_change_position_mode(dualSidePosition=False)
# print(response)

print("symbol is:", symbol)
# 开始前先取消所有symbol的挂单
strategy.close_all()

# 获取Futures账户信息
account_info = client.futures_account()
# 打印账户总余额
pprint_with_timestamp(f"{bcolors.OKGREEN}Bot started 初始总余额:{float(account_info['totalWalletBalance']):.2f} USDT{bcolors.ENDC}")

while True:
    print("--------------------------------------------------")
    # 获取账户信息
    info = client.futures_account()
    # 总未实现盈亏
    total_unrealized_pnl = float(info["totalUnrealizedProfit"])
    current_account_info = client.futures_account()
    balance = float(current_account_info["totalWalletBalance"]) - float(
        account_info["totalWalletBalance"]
    )
    if total_unrealized_pnl > 0:
        color_code = bcolors.OKGREEN
    else:
        color_code = bcolors.RED
    pprint_with_timestamp(
        f"{color_code}总未实现盈亏:{total_unrealized_pnl:.2f} 当前总盈亏: {balance:.2f} USDT{bcolors.ENDC}"
    )

    position_info = client.futures_position_information(symbol=symbol)
    for position in position_info:
        # 打印每个持仓的未实现盈利
        if float(position["positionAmt"]) != 0:  # 筛选出当前有持仓的合约
            pprint_with_timestamp(
                f"{color_code}Symbol: {position['symbol']}, entryPrice: {float(position['entryPrice']):.4f}, markPrice: {float(position['markPrice']):.4f}, Profit: {float(position['unRealizedProfit']):.2f} USDT {bcolors.ENDC}"
            )

    if strategy.should_open_long():
        # 执行买多操作
        order = strategy.open_long(quantity)
    elif strategy.should_open_short():
        # 执行买空操作
        order = strategy.open_short(quantity)

    if strategy.should_close(
        total_unrealized_pnl, target_profit_usdt, target_loss_usdt
    ):
        # 执行平仓操作
        sell_order = strategy.close_all()
        pprint_with_timestamp(f"Sold at {strategy.get_price()}")
        break
    time.sleep(2)

current_account_info = client.futures_account()
balance = float(current_account_info["totalWalletBalance"]) - float(
    account_info["totalWalletBalance"]
)
if total_unrealized_pnl > 0:
    color_code = bcolors.OKGREEN
else:
    color_code = bcolors.RED
pprint_with_timestamp(
    f"{color_code}最终总盈亏: {balance:.2f} USDT{bcolors.ENDC}"
)


