import time
from binance.client import Client
from binance.enums import *
import configparser
import argparse
from strategy.futures_bot_strategy import BasicBotStrategy

parser = argparse.ArgumentParser()
parser.add_argument('-t', action='store_true', help='for testnet')
args = parser.parse_args()

config = configparser.ConfigParser()
# reading config file
config.read("user.cfg")

# use testnet api_key pair for debug
if args.t:
    api_key = config.get("binance_user_config", "test_api_key")
    api_secret = config.get("binance_user_config", "test_api_secret")
    client = Client(api_key, api_secret, testnet=True, requests_params={'timeout': 50})
    strategy=BasicBotStrategy(client)
else:
    api_key = config.get("binance_user_config", "api_key")
    api_secret = config.get("binance_user_config", "api_secret")
    client = Client(api_key, api_secret, requests_params={'timeout': 50})
    strategy=BasicBotStrategy(client)

symbol = config.get("binance_user_config", "symbol")
quantity = float(config.get("binance_user_config", "quantity"))
target_profit = float(config.get("binance_user_config", "target_profit"))
stop_loss_profit = float(config.get("binance_user_config", "stop_loss_profit"))
target_profit_usdt = float(config.get("binance_user_config", "target_profit_usdt"))
target_loss_usdt = float(config.get("binance_user_config", "target_loss_usdt"))

# get the current price for the symbol
prices = client.get_symbol_ticker(symbol=symbol)
current_price = float(prices["price"])

notional = quantity * current_price
min_notional = 100.0
print("notional:", notional)
print("min quantity:", min_notional / current_price)
if notional < min_notional:
    quantity = min_notional / current_price

leverage = config.get("binance_user_config", "leverage")
response = client.futures_change_leverage(symbol=symbol, leverage=leverage)
print(response)

# position_mode = client.futures_get_position_mode()
# print("当前持仓模式:", "双向" if position_mode["dualSidePosition"] else "单向")
# 切换到对冲模式
# response = client.futures_change_position_mode(dualSidePosition=False)
# print(response)

def clearAllFuturesPosition(client):
    # clear all positions for testing.
    positions = client.futures_account()["positions"]
    for position in positions:
        symbol_tmp = position["symbol"]
        qty = float(position["positionAmt"])  # 当前持仓数量
        if qty != 0:  # 如果持有该合约的仓位不为0，则需要平仓
            if qty > 0:  # 如果是多头仓位，则需要卖出平仓
                order = client.futures_create_order(
                    symbol=symbol_tmp,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_MARKET,
                    quantity=abs(qty),
                )
            elif qty < 0:  # 如果是空头仓位，则需要买入平仓
                order = client.futures_create_order(
                    symbol=symbol_tmp,
                    side=SIDE_BUY,
                    type=ORDER_TYPE_MARKET,
                    quantity=abs(qty),
                )
            print(f"平仓订单已提交：{order}")

print("symbol is:", symbol)
clearAllFuturesPosition(client)

# 获取Futures账户信息
account_info = client.futures_account()

# 打印账户总余额
print("总余额:", account_info["totalWalletBalance"])

purchase_price = 0
BUY_FIRST = True

# 通过K线判断是买空还是买多
klines = client.get_historical_klines(
        symbol, Client.KLINE_INTERVAL_15MINUTE, "1 day ago UTC"
        )
last_klines = klines[-3:]
# 比较最早一次和最后一次K线的收盘价
first_close_price = float(last_klines[0][4])
last_close_price = float(last_klines[-1][4])
if last_close_price > first_close_price:
    print("总体趋势是上涨")
    BUY_FIRST = True
else:
    print("总体趋势是下跌")
    BUY_FIRST = False

if BUY_FIRST:
    buy_order = strategy.buy(symbol, quantity)
else:
    sell_order = strategy.sell(symbol, quantity)

while True:
    print("--------------------------------------------------")
    # 获取账户信息
    info = client.futures_account()
    # 总未实现盈亏
    total_unrealized_pnl = info["totalUnrealizedProfit"]
    print("总未实现盈亏:{:.2f} USDT".format(float(total_unrealized_pnl)))

    current_account_info = client.futures_account()
    # print("总余额:", current_account_info['totalWalletBalance'])
    print(
        "当前总盈亏:",
        float(current_account_info["totalWalletBalance"])
        - float(account_info["totalWalletBalance"]),
    )

    position_info = client.futures_position_information(symbol=symbol)
    for position in position_info:
        # 打印每个持仓的未实现盈利
        if float(position["positionAmt"]) != 0:  # 筛选出当前有持仓的合约
            print(
                f"""Symbol: {position['symbol']}, entryPrice: {position['entryPrice']}, markPrice: {position['markPrice']}, Profit: {position['unRealizedProfit']} USDT"""
            )
            if purchase_price != position["entryPrice"]:
                purchase_price = float(position["entryPrice"])
                print(f"purchase_price: {purchase_price}")

    if strategy.should_buy(symbol):
        # 执行买入操作
        buy_order = strategy.buy(symbol, quantity)
        purchase_price = strategy.get_price(symbol)
        print(f"Bought at {purchase_price}")

    # if should_sell(purchase_price):
    if strategy.should_sell_with_unrealized_pnl(total_unrealized_pnl, target_profit_usdt, target_loss_usdt):
        # 执行卖出操作
        sell_order = strategy.sell(symbol, quantity)
        print(f"Sold at {strategy.get_price(symbol)}")
    time.sleep(2)
