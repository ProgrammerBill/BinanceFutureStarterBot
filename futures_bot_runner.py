import time
from datetime import datetime
from binance.client import Client
from binance.enums import *
import pytz
import configparser

config = configparser.ConfigParser()

# reading config file
config.read('user.cfg')

# use testnet api_key pair for debug
api_key = config.get('binance_user_config', 'api_key')
api_secret = config.get('binance_user_config', 'api_secret')

client = Client(api_key, api_secret, testnet=True)

symbol = config.get('binance_user_config', 'symbol')
quantity = float(config.get('binance_user_config', 'quantity'))
target_profit = float(config.get('binance_user_config', 'target_profit'))
stop_loss_profit = float(config.get('binance_user_config', 'stop_loss_profit'))

# get the current price for the symbol
prices = client.get_symbol_ticker(symbol=symbol)
current_price = float(prices["price"])

notional = quantity * current_price
min_notional = 100.0
print("notional:", notional)
if notional < min_notional:
    quantity = min_notional / current_price

leverage = config.get('binance_user_config', 'leverage')
response = client.futures_change_leverage(symbol=symbol, leverage=leverage)
print(response)

#position_mode = client.futures_get_position_mode()
#print("当前持仓模式:", "双向" if position_mode["dualSidePosition"] else "单向")
# 切换到对冲模式
# response = client.futures_change_position_mode(dualSidePosition=False)
# print(response)

def get_price():
    # 获取当前市场价格
    avg_price = client.get_avg_price(symbol=symbol)
    return float(avg_price["price"])


def buy(symbol, quantity):
    # 执行买入操作
    print("buy with quantity:", quantity)
    order = client.futures_create_order(
        symbol=symbol, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quantity=quantity
    )
    return order


def sell(symbol, quantity):
    # 执行卖出操作
    print("sell with quantity:", quantity)
    order = client.futures_create_order(
        symbol=symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=quantity
    )
    return order


def should_buy():
    # 这里应该是你的买入逻辑，比如价格上升趋势
    position_info = client.futures_position_information(symbol=symbol)
    for position in position_info:
        if float(position["positionAmt"]) != 0:  # 筛选出当前有持仓的合约
            return False
    return True


def should_sell(purchase_price):
    # 当前价格达到目标盈利时返回True
    current_price = get_price()
    current_profit = (current_price - purchase_price) / purchase_price * 100
    print(f"current profit: {current_profit:.2f}%")
    if current_profit > target_profit or current_profit < stop_loss_profit:
        return True
    else:
        return False


# clear all positions for testing.
positions = client.futures_account()["positions"]
for position in positions:
    symbol_tmp = position["symbol"]
    qty = float(position["positionAmt"])  # 当前持仓数量
    if qty != 0:  # 如果持有该合约的仓位不为0，则需要平仓
        if qty > 0:  # 如果是多头仓位，则需要卖出平仓
            order = client.futures_create_order(
                symbol=symbol_tmp, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=abs(qty)
            )
        elif qty < 0:  # 如果是空头仓位，则需要买入平仓
            order = client.futures_create_order(
                symbol=symbol_tmp, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quantity=abs(qty)
            )
        print(f"平仓订单已提交：{order}")

print("symbol is:", symbol)

purchase_price = 0
while True:
   print("--------------------------------------------------")
   # 获取账户信息
   info = client.futures_account()
   # 总未实现盈亏
   total_unrealized_pnl = info['totalUnrealizedProfit']
   print("总未实现盈亏:{:.2f} USDT".format(float(total_unrealized_pnl)))

   position_info = client.futures_position_information(symbol=symbol)
   # print(position_info)
   for position in position_info:
       # 打印每个持仓的未实现盈利
       if float(position["positionAmt"]) != 0:  # 筛选出当前有持仓的合约
           print(
               f"""Symbol: {position['symbol']}, entryPrice: {position['entryPrice']}, markPrice: {position['markPrice']}, Profit: {position['unRealizedProfit']} USDT"""
           )
           if purchase_price != position["entryPrice"]:
               purchase_price = float(position["entryPrice"])
               print(f"purchase_price: {purchase_price}")
   if should_buy():
       # 执行买入操作
       buy_order = buy(symbol, quantity)
       purchase_price = get_price()
       print(f"Bought at {purchase_price}")

   if should_sell(purchase_price):
       # 执行卖出操作
       sell_order = sell(symbol, quantity)
       print(f"Sold at {get_price()}")
   time.sleep(5)  # 每5s检查一次，根据需要调整频率
