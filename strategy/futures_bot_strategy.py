from binance.client import Client
from binance.enums import *

class BasicBotStrategy:
    def __init__(self, client):
        self.client = client

    def get_price(self, symbol):
        # 获取当前市场价格
        avg_price = self.client.get_avg_price(symbol=symbol)
        return float(avg_price["price"])

    def buy(self, symbol, quantity):
        # 执行买入操作
        print("buy with quantity:", quantity)
        order = self.client.futures_create_order(
            symbol=symbol, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quantity=quantity
        )
        return order

    def sell(self, symbol, quantity):
        # 执行卖出操作
        print("sell with quantity:", quantity)
        order = self.client.futures_create_order(
            symbol=symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=quantity
        )
        return order


    def should_buy(self, symbol):
        # 这里应该是你的买入逻辑，比如价格上升趋势
        position_info = self.client.futures_position_information(symbol=symbol)
        for position in position_info:
            if float(position["positionAmt"]) != 0:  # 筛选出当前有持仓的合约
                return False
        return True


    def should_sell(self, symbol, purchase_price, target_profit, stop_loss_profit):
        # 当前价格达到目标盈利时返回True
        current_price = self.get_price(symbol)
        current_profit = (current_price - purchase_price) / purchase_price * 100
        print(f"current profit: {current_profit:.2f}%")
        if current_profit > target_profit or current_profit < stop_loss_profit:
            return True
        else:
            return False

    def should_sell_with_unrealized_pnl(self, total_unrealized_pnl, target_profit_usdt, target_loss_usdt):
        if float(total_unrealized_pnl) > target_profit_usdt or float(total_unrealized_pnl) < target_loss_usdt:
            return True
        else:
            return False
