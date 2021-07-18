import backtrader as bt
from backtrader.indicators.ema import ExponentialMovingAverage
from backtrader.indicators import *
import queue
from collections import deque
import datetime
import pandas as pd
from collections import deque


class TwentyTen(bt.Strategy):
    params = (
        ("maperiod", 10),
        ("printLog", False),
        ("StopProfit", 1.05),
    )

    def log(self, txt, dt=None, doprint=False):
        """ Logging function fot this strategy"""
        if self.params.printLog or doprint:
            dt = dt or self.datas[0].datetime.datetime(0)
            print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.volume = self.datas[0].volume

        self.cursize = 0

        self.commission = 0.001
        self.leverage = 1
        self.interest = 0.001
        self.startcash = 100000
        self.curcash = 100000
        self.buysizeRatio = 0.91
        self.positionValue = 0
        self.margincall = 0
        self.profitlistplus = pd.DataFrame()
        self.profitlistminus = pd.DataFrame()

        self.longwindow = 10
        self.sellwindow = 10

        self.queue20 = deque(maxlen=self.longwindow)
        self.queue10 = deque(maxlen=self.sellwindow)

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.sellprice = None
        self.buycomm = None
        self.buylen = 0
        self.wincnt = 0
        self.losecnt = 0
        self.tiecnt = 0
        self.RSIState = {
            "state": "not initialized",
            "len": 0,
            "price": 0,
            "prersi": 0,
            "rsi": 0,
        }

        # State
        self.momentumCnt = 0

        # Trend Indicators
        self.sma5 = bt.indicators.SimpleMovingAverage(self.datas[0], period=5)
        self.sma10 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=10)
        self.sma20 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=20)
        self.sma40 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=40)
        self.sma60 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=60)
        self.RSI = bt.indicators.RelativeStrengthIndex(
            self.datas[0], period=14, movav=MovingAverageSimple
        )
        self.macd = bt.indicators.MACD(
            self.datas[0], plot=True, movav=ExponentialMovingAverage)

        # Momentum Indicators
        # bt.indicators.StochasticSlow(self.datas[0])

        # Market Intensity
        # bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=7)
        # bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=14)
        self.vsma5 = bt.indicators.SimpleMovingAverage(
            self.datas[0].volume, period=5)
        self.vsma10 = bt.indicators.SimpleMovingAverage(
            self.datas[0].volume, period=10, plot=False
        )

        self.vmacd = bt.indicators.MACD(
            self.datas[0].volume,
            period_me1=14,
            period_me2=21,
            period_signal=4,
            plot=False,
        )

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    "BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                self.positionValue = order.executed.value

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.buylen = len(self)
            else:  # Sell
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                curValue = abs(order.executed.price * order.executed.size)
                profitRate = (curValue - self.positionValue) / \
                    self.positionValue
                buyValue = ((self.curcash * self.buysizeRatio) * self.leverage)
                interestMinus = ((buyValue - self.curcash) * self.interest)
                commsMinus = buyValue * self.commission  # when buy
                commsMinus = commsMinus + \
                    ((buyValue + (buyValue*profitRate))
                     * self.commission)  # when sell
                self.curcash = self.curcash + \
                    (buyValue * profitRate) - commsMinus
                if self.leverage > 1:
                    self.curcash = self.curcash - interestMinus

                if profitRate >= 0:
                    self.profitlistplus = self.profitlistplus.append(
                        pd.DataFrame({'Profit': profitRate}, index=[len(self.profitlistplus)]))
                else:
                    self.profitlistminus = self.profitlistminus.append(
                        pd.DataFrame({'Profit': abs(profitRate)}, index=[len(self.profitlistminus)]))

                if order.executed.price > self.buyprice:
                    self.wincnt += 1
                elif order.executed.price < self.buyprice:
                    self.losecnt += 1
                else:
                    self.tiecnt += 1
                self.sellprice = order.executed.price

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log("OPERATION PROFIT, GROSS %.2f, NET %.2f" %
                 (trade.pnl, trade.pnlcomm))

    def save_RSI(self, statestr, length, price, rsi):
        self.RSIState["state"] = statestr
        self.RSIState["len"] = length
        self.RSIState["price"] = price
        self.RSIState["prersi"] = self.RSIState["rsi"]
        self.RSIState["rsi"] = rsi

    def RSIstatemachine(self):
        retval = 0
        rsiBoundry = 30
        rsiGapValue = 30

        if self.RSIState["state"] == "not initialized":
            for i in range(-(self.longwindow-1), 1):
                self.queue20.append(self.dataclose[i])
                # self.queue20.put(self.dataclose[i])

            for i in range(-(self.sellwindow-1), 1):
                self.queue10.append(self.dataclose[i])

            self.save_RSI("not started", len(self),
                          self.dataclose[0], self.RSI[0])

        if len(self) != self.RSIState["len"]:

            if self.RSIState["state"] == "not started":
                maxprice = max(self.queue20)
                if maxprice < self.dataclose[0]:
                    retval = 1
                    self.save_RSI("buy", len(self),
                                  self.dataclose[0], self.RSI[0])


            elif self.RSIState["state"] == "buy":
                if not self.position:
                    return retval
                minprice = min(self.queue10)
                if minprice > self.dataclose[0]:
                # if self.dataclose[0] <= self.buyprice * 0.92:
                    retval = -1

                    self.save_RSI("not started", len(self),
                                  self.dataclose[0], self.RSI[0])

            if len(self.queue20) == self.queue20.maxlen:
                self.queue20.popleft()
                self.queue20.append(self.dataclose[0])

            if len(self.queue10) == self.queue10.maxlen:
                self.queue10.popleft()
                self.queue10.append(self.dataclose[0])



        return retval

    def next(self):
        # Simply log the closing price of the series from the reference
        # self.log("Close, %.2f" % self.dataclose[0])
        # Check if an order is pending ... if yes, we cannot send a 2nd one

        if self.order:
            return

        # Check if we are in the market
        if not self.position:  # to Buy
            nBuy = self.RSIstatemachine()
            if nBuy == 1:
                self.log("BUY CREATE, %.2f" % self.dataclose[0])
                self.cursize = self.broker.get_cash() / self.dataclose[0]
                self.cursize = self.cursize * 0.91
                self.order = self.buy(size=int(self.cursize))

        else:  # to Sell
            if (((self.dataclose[0] - self.buyprice) / self.buyprice) * self.leverage) < -0.95:
                self.margincall = 1
            if True or self.buylen + 1 < len(self):
                nSell = self.RSIstatemachine()
                if nSell == -1:
                    self.log("SELL CREATE, %.2f" % self.dataclose[0])
                    self.order = self.sell(size=int(self.cursize))

                # if self.dataclose[0] <= self.buyprice * 0.97:
                #     # SELL, SELL, SELL!!! (with all possible default parameters)
                #     self.log("SELL CREATE, %.2f" % self.dataclose[0])

                #     # Keep track of the created order to avoid a 2nd order
                #     self.order = self.sell()

                # # self.macd.lines.macd[0] < self.macd.lines.signal[0]:
                # # self.RSI[0] >= 70:

                # # (self.dataclose[0] >= self.buyprice * 1.07) or
                # elif self.RSI[0] >= 70:
                #     # SELL, SELL, SELL!!! (with all possible default parameters)
                #     self.log("SELL CREATE, %.2f" % self.dataclose[0])

                #     # Keep track of the created order to avoid a 2nd order
                #     self.order = self.sell()

    def stop(self):

        if self.position:
            profitRate = (self.dataclose[0] - self.buyprice) / self.buyprice
            buyValue = ((self.curcash * self.buysizeRatio) * self.leverage)
            self.curcash = self.curcash + (buyValue * profitRate)

        if self.margincall == 1:
            self.curcash = 0

        self.log(
            "(MA Period %2d) Ending Value %.2f Margin Result %.2f"
            % (self.params.maperiod, self.broker.getvalue(), self.curcash),
            doprint=True,
        )
        self.log(
            "Won Count: %d, Lost Count: %d, Tie Count: %d"
            % (self.wincnt, self.losecnt, self.tiecnt),
            doprint=True,
        )
