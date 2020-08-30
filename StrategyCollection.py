
import backtrader as bt

class MyFirstStrategy(bt.Strategy):
    params = (
        ('maperiod', 10),
        ('printLog', False),
        ('momentumLasting', 10),
    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function fot this strategy'''
        if self.params.printLog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

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
        self.sma10 = bt.indicators.SimpleMovingAverage(self.datas[0], period = 10)
        self.sma20 = bt.indicators.SimpleMovingAverage(self.datas[0], period = 20)
        self.sma40 =  bt.indicators.SimpleMovingAverage(self.datas[0], period = 40)
        self.macd = bt.indicators.MACDHisto(self.datas[0], plot=False)

        # Momentum Indicators
        # bt.indicators.StochasticSlow(self.datas[0])

        # Volitality Indicators
        self.ATR = bt.indicators.ATR(self.datas[0], plot=False)

        # Market Intensity
        # bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=7)
        # bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=14)
        self.vsma5 = bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=5)
        self.vsma10 = bt.indicators.SimpleMovingAverage(self.datas[0].volume, period=10, plot=False)
        self.vmacd = bt.indicators.MACD(self.datas[0].volume, period_me1=7, period_me2=14 ,period_signal=4, plot=False)
        self.RSI = bt.indicators.RSI(self.datas[0], period=10)

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
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                if order.executed.price > self.buyprice:
                    self.wincnt += 1
                elif order.executed.price < self.buyprice:
                    self.losecnt += 1
                else:
                    self.tiecnt += 1


            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

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
        if not self.position:   # to Buy

            # Not yet ... we MIGHT BUY if ...
            # if self.dataclose[0] > self.sma10[0]:
            #
            #     # BUY, BUY, BUY!!! (with all possible default parameters)
            #     self.log('BUY CREATE, %.2f' % self.dataclose[0])
            #
            #     # Keep track of the created order to avoid a 2nd order
            #     self.order = self.buy()
            if self.RSI[0] < 40:
                if self.dataclose[0] > self.sma10[0]:
                    # if self.volume[0] > self.vsma5:
                        self.log('BUY CREATE, %.2f' % self.dataclose[0])
                        self.order = self.buy()

        else:   # to Sell

            if self.dataclose[0] < self.sma10[0] or self.dataclose[0] < (self.buyprice):
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()

    def stop(self):
        self.log('(MA Period %2d) Ending Value %.2f' %
                 (self.params.maperiod, self.broker.getvalue()), doprint=True)
        self.log('Won Count: %d, Lost Count: %d, Tie Count: %d' %
                 (self.wincnt, self.losecnt, self.tiecnt), doprint=True)