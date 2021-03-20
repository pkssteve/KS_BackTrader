import backtrader as bt
from backtrader.indicators.ema import ExponentialMovingAverage
import CustumIndicators as ci
import queue
from collections import deque
import datetime


class RSIMomentum(bt.Strategy):
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

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
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
            self.datas[0], period=14, movav=ExponentialMovingAverage
        )
        self.macd = bt.indicators.MACDHisto(self.datas[0], plot=True)

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

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.buylen = len(self)
            else:  # Sell
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                if order.executed.price > self.buyprice:
                    self.wincnt += 1
                elif order.executed.price < self.buyprice:
                    self.losecnt += 1
                else:
                    self.tiecnt += 1

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
        if self.RSIState["state"] == "not initialized":
            self.save_RSI("not started", len(self),
                          self.dataclose[0], self.RSI[0])

        if len(self) != self.RSIState["len"]:

            if self.RSIState["state"] == "not started":
                if (self.RSI[0] > self.RSI[-1] and self.RSI[-1] <= 30):  # and self.RSI[0] > 30
                    self.save_RSI("RSI momentum", len(self),
                                  self.dataclose[0], self.RSI[-1])

            elif self.RSIState["state"] == "RSI momentum":
                if self.RSI[0] < 30 or self.RSI[0] > 65:
                    self.save_RSI("not started", len(self),
                                  self.dataclose[0], self.RSI[-1])
                elif self.macd.lines.macd[0] > self.macd.lines.signal[0]:
                    self.save_RSI("MACD cross", len(self),
                                  self.dataclose[0], self.RSI[-1])

            elif self.RSIState["state"] == "MACD cross":
                retval = 1
                self.save_RSI("not started", len(self),
                              self.dataclose[0], self.RSI[-1])

            elif self.RSIState["state"] == "buy":
                print("To do")
            elif self.RSIState["state"] == "sell and again1":
                print("To do")
            elif self.RSIState["state"] == "sell and again2":
                print("To do")
            elif self.RSIState["state"] == "finish":
                print("To do")
            elif self.RSIState["state"] == "sell and wait":
                print("To do")

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
                self.order = self.buy()

        else:  # to Sell
            if self.buylen + 1 < len(self):
                if self.dataclose[0] <= self.buyprice * 0.97:
                    # SELL, SELL, SELL!!! (with all possible default parameters)
                    self.log("SELL CREATE, %.2f" % self.dataclose[0])

                    # Keep track of the created order to avoid a 2nd order
                    self.order = self.sell()

                # self.macd.lines.macd[0] < self.macd.lines.signal[0]:
                # self.RSI[0] >= 70:

                # (self.dataclose[0] >= self.buyprice * 1.07) or
                elif self.RSI[0] >= 70:
                    # SELL, SELL, SELL!!! (with all possible default parameters)
                    self.log("SELL CREATE, %.2f" % self.dataclose[0])

                    # Keep track of the created order to avoid a 2nd order
                    self.order = self.sell()

    def stop(self):
        self.log(
            "(MA Period %2d) Ending Value %.2f"
            % (self.params.maperiod, self.broker.getvalue()),
            doprint=True,
        )
        self.log(
            "Won Count: %d, Lost Count: %d, Tie Count: %d"
            % (self.wincnt, self.losecnt, self.tiecnt),
            doprint=True,
        )


class MomentumTrackingStrategy(bt.Strategy):
    params = (
        ("maperiod", 10),
        ("printLog", False),
        ("momentumLasting", 40),
        ("expectedProfit", 0.01),
        ("lowboundRSI", 25),
        ("lowboundRSI2", 30),
        ("upperboundRSI", 50),
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
        self.peakqueue = deque(maxlen=6)
        self.latestHigh = 0
        self.historycalHigh = 0

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Statistics
        self.wincnt = 0
        self.losecnt = 0
        self.tiecnt = 0

        # State
        self.momentumCnt = 0
        self.holdcnt = 0
        self.rebuy = 0

        # Criteria
        self.targetPrice = 0
        self.escapePrice = 0

        # Trend Indicators
        self.sma3 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=3
        )  # for peak detection
        self.sma10 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=10)
        self.sma20 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=20)
        self.sma40 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=40)
        self.sma60 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=60)
        self.macd = bt.indicators.MACD(
            self.datas[0], period_me1=24, period_me2=48)
        self.atr = bt.indicators.AverageTrueRange(
            self.datas[0], period=14, plot=False)
        self.macdCross = bt.indicators.CrossOver(
            self.macd.lines.macd, self.macd.lines.signal, plot=False
        )

        # Momentum Indicators
        # bt.indicators.StochasticSlow(self.datas[0])

        # Volitality Indicators
        # self.ATR = bt.indicators.ATR(self.datas[0], plot=False)

        # Market Intensity
        # bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=7)
        # bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=14)
        # self.vsma5 = bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=5)
        # self.vsma10 = bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=10, plot=False)
        self.vema48 = bt.indicators.ExponentialMovingAverage(
            self.datas[0].volume, period=48, subplot=True, plot=False
        )
        # self.vsma48 = bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=48, plot=False)
        # self.vmacd = bt.indicators.MACD(self.datas[0].volume, period_me1=7, period_me2=14, period_signal=4, plot=False)
        self.RSI = bt.indicators.RelativeStrengthIndex(
            self.datas[0], period=14)
        self.RSIFalling = 1

        # self.vr = ci.VolumeRatio(self.datas[0])

        # Indicators for the plotting show
        # bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        # bt.indicators.WeightedMovingAverage(self.datas[0], period=25, subplot=True)

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

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                if order.executed.price > self.buyprice:
                    self.wincnt += 1
                elif order.executed.price < self.buyprice:
                    self.losecnt += 1
                else:
                    self.tiecnt += 1

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

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log("Close, %.2f" % self.dataclose[0])

        if self.sma3[-2] < self.sma3[-1] and self.sma3[-1] < self.sma3[0]:
            self.peakqueue.appendleft(self.sma3[-1])

        self.latestHigh = self.peakqueue[0]
        self.historicalHigh = 0
        presma3 = 0
        for sma3 in self.peakqueue:
            if presma3 > sma3:
                break
            self.historicalHigh = sma3
            presma3 = sma3

        # listTrue = [1 for a in self.RSIFalling[-40:0] if a == 1]
        # numRSIFalling = listTrue.count

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        if self.momentumCnt > 0:
            self.momentumCnt += 1
            self.momentumCnt = self.momentumCnt % self.params.momentumLasting

        # Strong Momentum (in other view, bearish risk)
        if (
            self.RSI[0] <= self.params.lowboundRSI
            and self.RSI[-1] > self.params.lowboundRSI
        ):
            self.momentumCnt = 1

        # Check if we are in the market
        if not self.position:  # to Buy

            # Not yet ... we MIGHT BUY if ...

            if self.momentumCnt > 0:
                if self.RSI[0] >= self.params.upperboundRSI:
                    self.momentumCnt = 0

                if (
                    self.RSI[0] > self.RSI[-1]
                    and self.RSI[-1] <= self.params.lowboundRSI2
                    and self.RSI[0] > self.params.lowboundRSI2
                ):
                    self.order = self.buy()
                    self.escapePrice = self.dataclose[0] * 0.98

        else:  # to Sell

            # escape condition
            if self.dataclose[0] <= self.escapePrice:
                self.log("SELL CREATE, %.2f" % self.dataclose[0])
                self.order = self.sell()
                if self.momentumCnt > 0:
                    self.rebuy = 1

            # profit condition
            if self.RSI[0] >= self.params.upperboundRSI:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log("SELL CREATE, %.2f" % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()
                self.momentumCnt = 0

    def stop(self):
        self.log(
            "(MomentumLasting %2d, Expected Profit %.3f) Ending Value %.2f"
            % (
                self.params.momentumLasting,
                self.params.expectedProfit,
                self.broker.getvalue(),
            ),
            doprint=True,
        )
        self.log(
            "Won Count: %d, Lost Count: %d, Tie Count: %d"
            % (self.wincnt, self.losecnt, self.tiecnt),
            doprint=True,
        )


class LongTrendStrategy(bt.Strategy):
    params = (
        ("maperiod", 10),
        ("printLog", False),
        ("momentumLasting", 40),
        ("expectedProfit", 0.01),
    )

    def log(self, txt, dt=None, doprint=False):
        """ Logging function fot this strategy"""
        if self.params.printLog or doprint:
            dt = dt or self.datas[0].datetime.datetime(0)
            print("%s, %s" % (dt.isoformat(), txt))

    def examineCandle(self):
        ret = 0

        # calc source values
        preDiff = abs(self.data.close[-1] - self.data.open[-1])
        curDiff = abs(self.data.close[0] - self.data.open[0])

        direction = list()
        for i in range(3):
            direction.append(
                1 if self.data.close[i - 2] > self.data.open[i - 2] else 0)

        # decision logic
        if self.dataclose[0] > self.dataclose[-1] or direction[2] == 1:
            ret = 1
        if (direction[2] == 1) and (curDiff > preDiff):
            ret = 2

        return ret

    def examineVolume(self):
        return 1 if self.data.volume[0] > self.data.volume[-1] else 0

    def calcPossibleProfit(self, curPrice, elderPrice):
        profit = 0
        dividedby3 = abs((elderPrice - curPrice) / 3)
        profit = (
            (dividedby3 / curPrice)
            if (dividedby3 / curPrice) >= self.params.expectedProfit
            else 0
        )
        return profit

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.volume = self.datas[0].volume
        self.peakqueue = deque(maxlen=6)
        self.latestHigh = 0
        self.historycalHigh = 0

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Statistics
        self.wincnt = 0
        self.losecnt = 0
        self.tiecnt = 0

        # State
        self.momentumCnt = 0
        self.holdcnt = 5

        # Criteria
        self.targetPrice = 0
        self.escapePrice = 0

        # Trend Indicators
        self.sma3 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=3
        )  # for peak detection
        # self.sma10 = bt.indicators.SimpleMovingAverage(self.datas[0], period=10)
        # self.sma20 = bt.indicators.SimpleMovingAverage(self.datas[0], period=20)
        # self.sma40 = bt.indicators.SimpleMovingAverage(self.datas[0], period=40)
        self.sma60 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=60)
        self.macd = bt.indicators.MACD(
            self.datas[0], period_me1=24, period_me2=48)
        self.atr = bt.indicators.AverageTrueRange(self.datas[0], period=14)
        self.macdCross = bt.indicators.CrossOver(
            self.macd.lines.macd, self.macd.lines.signal
        )

        # Momentum Indicators
        # bt.indicators.StochasticSlow(self.datas[0])

        # Volitality Indicators
        # self.ATR = bt.indicators.ATR(self.datas[0], plot=False)

        # Market Intensity
        # bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=7)
        # bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=14)
        # self.vsma5 = bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=5)
        # self.vsma10 = bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=10, plot=False)
        self.vema48 = bt.indicators.ExponentialMovingAverage(
            self.datas[0].volume, period=48, subplot=True
        )
        # self.vsma48 = bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=48, plot=False)
        # self.vmacd = bt.indicators.MACD(self.datas[0].volume, period_me1=7, period_me2=14, period_signal=4, plot=False)
        self.RSI = bt.indicators.RelativeStrengthIndex(
            self.datas[0], period=14)
        # self.vr = ci.VolumeRatio(self.datas[0])

        # Indicators for the plotting show
        # bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        # bt.indicators.WeightedMovingAverage(self.datas[0], period=25, subplot=True)

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

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                if order.executed.price > self.buyprice:
                    self.wincnt += 1
                elif order.executed.price < self.buyprice:
                    self.losecnt += 1
                else:
                    self.tiecnt += 1

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

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log("Close, %.2f" % self.dataclose[0])

        if self.sma3[-2] < self.sma3[-1] and self.sma3[-1] < self.sma3[0]:
            self.peakqueue.appendleft(self.sma3[-1])

        self.latestHigh = self.peakqueue[0]
        self.historicalHigh = 0
        presma3 = 0
        for sma3 in self.peakqueue:
            if presma3 > sma3:
                break
            self.historicalHigh = sma3
            presma3 = sma3

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        if self.momentumCnt > 0:
            self.momentumCnt += 1
            self.momentumCnt = self.momentumCnt % self.params.momentumLasting
        else:
            if self.RSI[0] < 30:  # and self.RSI[0] > self.RSI[-1]
                self.momentumCnt += 1

        # Check if we are in the market
        if not self.position:  # to Buy

            # Not yet ... we MIGHT BUY if ...
            # if self.dataclose[0] > self.sma10[0]:
            #
            #     # BUY, BUY, BUY!!! (with all possible default parameters)
            #     self.log('BUY CREATE, %.2f' % self.dataclose[0])
            #
            #     # Keep track of the created order to avoid a 2nd order
            #     self.order = self.buy()

            if self.momentumCnt > 0:
                if self.macdCross[0] == 1:
                    if self.datas[0].volume[0] > self.vema48[0]:
                        self.log("BUY CREATE, %.2f" % self.dataclose[0])
                        self.order = self.buy()
                        # self.targetPrice = self.dataclose[0] * expectProf
                        self.escapePrice = self.dataclose[0]
                        self.momentumCnt = 0

        else:  # to Sell
            if self.holdcnt > 0:
                self.holdcnt -= 1
                return

            if self.macdCross[0] == -1:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log("SELL CREATE, %.2f" % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()
                self.holdcnt = 5

    def stop(self):
        self.log(
            "(MomentumLasting %2d, Expected Profit %.3f) Ending Value %.2f"
            % (
                self.params.momentumLasting,
                self.params.expectedProfit,
                self.broker.getvalue(),
            ),
            doprint=True,
        )
        self.log(
            "Won Count: %d, Lost Count: %d, Tie Count: %d"
            % (self.wincnt, self.losecnt, self.tiecnt),
            doprint=True,
        )


class MyFirstStrategy(bt.Strategy):
    params = (
        ("maperiod", 10),
        ("printLog", False),
        ("momentumLasting", 30),
        ("expectedProfit", 0.01),
    )

    def log(self, txt, dt=None, doprint=False):
        """ Logging function fot this strategy"""
        if self.params.printLog or doprint:
            dt = dt or self.datas[0].datetime.datetime(0)
            print("%s, %s" % (dt.isoformat(), txt))

    def examineCandle(self):
        ret = 0

        # calc source values
        preDiff = abs(self.data.close[-1] - self.data.open[-1])
        curDiff = abs(self.data.close[0] - self.data.open[0])

        direction = list()
        for i in range(3):
            direction.append(
                1 if self.data.close[i - 2] > self.data.open[i - 2] else 0)

        # decision logic
        if self.dataclose[0] > self.dataclose[-1] or direction[2] == 1:
            ret = 1
        if (direction[2] == 1) and (curDiff > preDiff):
            ret = 2

        return ret

    def examineVolume(self):
        return 1 if self.data.volume[0] > self.data.volume[-1] else 0

    def calcPossibleProfit(self, curPrice, elderPrice):
        profit = 0
        dividedby3 = abs((elderPrice - curPrice) / 3)
        profit = (
            (dividedby3 / curPrice)
            if (dividedby3 / curPrice) >= self.params.expectedProfit
            else 0
        )
        return profit

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.volume = self.datas[0].volume

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Statistics
        self.wincnt = 0
        self.losecnt = 0
        self.tiecnt = 0

        # State
        self.momentumCnt = 0
        self.holdcnt = 5

        # Criteria
        self.targetPrice = 0
        self.escapePrice = 0

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
        # self.macd = bt.indicators.MACDHisto(self.datas[0], plot=False)

        # Momentum Indicators
        # bt.indicators.StochasticSlow(self.datas[0])

        # Volitality Indicators
        # self.ATR = bt.indicators.ATR(self.datas[0], plot=False)

        # Market Intensity
        # bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=7)
        # bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=14)
        # self.vsma5 = bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=5)
        # self.vsma10 = bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=10, plot=False)
        # self.vmacd = bt.indicators.MACD(self.datas[0].volume, period_me1=7, period_me2=14, period_signal=4, plot=False)
        self.RSI = bt.indicators.RelativeStrengthIndex(
            self.datas[0], period=10)
        # self.vr = ci.VolumeRatio(self.datas[0])

        # Indicators for the plotting show
        # bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        # bt.indicators.WeightedMovingAverage(self.datas[0], period=25, subplot=True)

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

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                if order.executed.price > self.buyprice:
                    self.wincnt += 1
                elif order.executed.price < self.buyprice:
                    self.losecnt += 1
                else:
                    self.tiecnt += 1

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

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log("Close, %.2f" % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        if self.momentumCnt > 0:
            self.momentumCnt += 1
            self.momentumCnt = self.momentumCnt % self.params.momentumLasting
        else:
            if self.RSI[0] < 30:  # and self.RSI[0] > self.RSI[-1]
                self.momentumCnt += 1

        # Check if we are in the market
        if not self.position:  # to Buy

            # Not yet ... we MIGHT BUY if ...
            # if self.dataclose[0] > self.sma10[0]:
            #
            #     # BUY, BUY, BUY!!! (with all possible default parameters)
            #     self.log('BUY CREATE, %.2f' % self.dataclose[0])
            #
            #     # Keep track of the created order to avoid a 2nd order
            #     self.order = self.buy()

            if self.momentumCnt > 0:
                expectProf = self.calcPossibleProfit(
                    self.dataclose[0], self.sma60[0])
                if self.examineCandle() > 0 and expectProf > 0:
                    self.log("BUY CREATE, %.2f" % self.dataclose[0])
                    self.order = self.buy()
                    self.targetPrice = self.dataclose[0] * expectProf
                    self.escapePrice = self.dataclose[0]
                    self.momentumCnt = 0

        else:  # to Sell
            if self.holdcnt > 0:
                self.holdcnt -= 1
                return

            if self.dataclose[0] >= self.targetPrice or self.dataclose[0] <= (
                self.buyprice
            ):
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log("SELL CREATE, %.2f" % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()
                self.holdcnt = 5

    def stop(self):
        self.log(
            "(MomentumLasting %2d, Expected Profit %.3f) Ending Value %.2f"
            % (
                self.params.momentumLasting,
                self.params.expectedProfit,
                self.broker.getvalue(),
            ),
            doprint=True,
        )
        self.log(
            "Won Count: %d, Lost Count: %d, Tie Count: %d"
            % (self.wincnt, self.losecnt, self.tiecnt),
            doprint=True,
        )


class DefaultSampleStrategy(bt.Strategy):
    params = (
        ("maperiod", 10),
        ("printLog", False),
        ("momentumLasting", 10),
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

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.wincnt = 0
        self.losecnt = 0
        self.tiecnt = 0

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
            self.datas[0], period=10, movav=ExponentialMovingAverage
        )
        self.macd = bt.indicators.MACDHisto(self.datas[0], plot=False)

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
            period_me1=7,
            period_me2=14,
            period_signal=4,
            plot=False,
        )

        # Indicators for the plotting show
        # bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        # bt.indicators.WeightedMovingAverage(self.datas[0], period=25, subplot=True)

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

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                if order.executed.price > self.buyprice:
                    self.wincnt += 1
                elif order.executed.price < self.buyprice:
                    self.losecnt += 1
                else:
                    self.tiecnt += 1

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

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log("Close, %.2f" % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        if self.momentumCnt > 0:
            self.momentumCnt += 1
            self.momentumCnt = self.momentumCnt % self.params.momentumLasting
        else:
            if self.RSI[0] < 30 and self.RSI[0] > self.RSI[-1]:
                self.momentumCnt += 1

        # Check if we are in the market
        if not self.position:  # to Buy

            # Not yet ... we MIGHT BUY if ...
            # if self.dataclose[0] > self.sma10[0]:
            #
            #     # BUY, BUY, BUY!!! (with all possible default parameters)
            #     self.log('BUY CREATE, %.2f' % self.dataclose[0])
            #
            #     # Keep track of the created order to avoid a 2nd order
            #     self.order = self.buy()
            if self.momentumCnt > 0:
                if self.dataclose[0] > self.sma10[0] and self.sma10[0] < self.sma20[0]:
                    # if self.volume[0] > self.vsma5:
                    self.log("BUY CREATE, %.2f" % self.dataclose[0])
                    self.order = self.buy()

        else:  # to Sell

            if self.dataclose[0] < self.sma10[0] or self.dataclose[0] < (self.buyprice):
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log("SELL CREATE, %.2f" % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()

    def stop(self):
        self.log(
            "(MA Period %2d) Ending Value %.2f"
            % (self.params.maperiod, self.broker.getvalue()),
            doprint=True,
        )
        self.log(
            "Won Count: %d, Lost Count: %d, Tie Count: %d"
            % (self.wincnt, self.losecnt, self.tiecnt),
            doprint=True,
        )
