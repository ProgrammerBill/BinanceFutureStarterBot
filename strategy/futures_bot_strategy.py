from binance.client import Client
from binance.enums import *

class BasicBotStrategy:
    def __init__(self, client, symbol):
        self.client = client
        self.symbol = symbol

    def get_price(self):
        # 获取当前市场价格
        avg_price = self.client.get_avg_price(symbol=self.symbol)
        return float(avg_price["price"])

    def open_long(self, quantity):
        # 执行做多操作
        print("open_long with quantity:", quantity)
        order = self.client.futures_create_order(
            symbol=self.symbol, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quantity=quantity
        )
        return order

    def open_short(self, quantity):
        # 执行做空操作
        print("sell with quantity:", quantity)
        order = self.client.futures_create_order(
            symbol=self.symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
        )
        return order

    def close_all(self):
        positions = self.client.futures_account()["positions"]
        for position in positions:
            symbol_tmp = position["symbol"]
            if symbol_tmp == self.symbol:
                qty = float(position["positionAmt"])  # 当前持仓数量
                if qty != 0:  # 如果持有该合约的仓位不为0，则需要平仓
                    print("qty is", qty)
                    if qty > 0:  # 如果是多头仓位，则需要卖出平仓
                        self.client.futures_create_order(
                            symbol=symbol_tmp,
                            side=SIDE_SELL,
                            type=ORDER_TYPE_MARKET,
                            quantity=abs(qty),
                        )
                    elif qty < 0:  # 如果是空头仓位，则需要买入平仓
                        self.client.futures_create_order(
                            symbol=symbol_tmp,
                            side=SIDE_BUY,
                            type=ORDER_TYPE_MARKET,
                            quantity=abs(qty),
                        )
                    print("close order with qty:", qty)

    def should_open_long(self):
        # 如果已经有持仓，则不需要再开仓
        position_info = self.client.futures_position_information(symbol=self.symbol)
        for position in position_info:
            if float(position["positionAmt"]) != 0:  # 筛选出当前有持仓的合约
                return False
        klines = self.client.get_historical_klines(
                self.symbol, Client.KLINE_INTERVAL_15MINUTE, "1 day ago UTC"
                )
        last_klines = klines[-3:]
        # 比较最早一次和最后一次K线的收盘价
        first_close_price = float(last_klines[0][4])
        last_close_price = float(last_klines[-1][4])
        if last_close_price > first_close_price:
            print("总体趋势是上涨, 买空")
            return False
        else:
            return True

    def should_open_short(self):
        # 如果已经有持仓，则不需要再开仓
        position_info = self.client.futures_position_information(symbol=self.symbol)
        for position in position_info:
            if float(position["positionAmt"]) != 0:  # 筛选出当前有持仓的合约
                return False
        klines = self.client.get_historical_klines(
                self.symbol, Client.KLINE_INTERVAL_15MINUTE, "1 day ago UTC"
                )
        last_klines = klines[-3:]
        # 比较最早一次和最后一次K线的收盘价
        first_close_price = float(last_klines[0][4])
        last_close_price = float(last_klines[-1][4])
        if last_close_price > first_close_price:
            return False
        else:
            print("总体趋势是下跌, 买空")
            return True

    # 判断是否需要平仓, 当前的未实现盈亏超过目标盈利或者亏损超过目标亏损, 需要平仓
    # total_unrealized_pnl: 总的未实现盈亏
    # target_profit_usdt: 目标盈利
    # target_loss_usdt: 目标亏损
    def should_close(self, total_unrealized_pnl, target_profit_usdt, target_loss_usdt):
        if (
            float(total_unrealized_pnl) > target_profit_usdt
            or float(total_unrealized_pnl) < target_loss_usdt
        ):
            return True
        else:
            return False
