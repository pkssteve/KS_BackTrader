# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from __future__ import absolute_import, division, print_function, unicode_literals

import pandas as pd
from pandas_datareader import data as web

import numpy as np
import argparse
import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import time

# import cufflinks as cf
# import chart_studio.plotly as py
# import chart_studio
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo

# import plotly.plotly as py2
# import plotly
# import plotly.io as pio

# Import the backtrader platform
import backtrader as bt

import StrategyCollection as sc
import RSI_Simple as rs
import Buy_Hold as bh
import RSI_Farm as rf
import ST20_10 as tt
import ST_MA5 as ma
import ST_Volatibility as vol

if __name__ == "__main__":
    # Create a cerebro entity
    cerebro = bt.Cerebro(stdstats=False)

    # Add a strategy
    # cerebro.addstrategy(bh.BuyAndHold, printLog=True)
    # cerebro.addstrategy(rs.RSISimple, printLog=True)
    # cerebro.addstrategy(sc.RSIMomentum, printLog=True)
    # cerebro.addstrategy(rf.RSIFarm, printLog=True)
    # cerebro.addstrategy(tt.TwentyTen, printLog=True)
    # cerebro.addstrategy(ma.MA5, printLog=True)
    cerebro.addstrategy(vol.VOLA, printLog=True)

    # strats = cerebro.optstrategy(
    #     sc.MyFirstStrategy,
    #     momentumLasting=range(5,6),R
    #     expectedProfit =numpy.arange(0.01, 0.04, 0.01)
    # )

    cerebro.addobserver(bt.observers.Value)
    cerebro.addobserver(bt.observers.Trades)
    cerebro.addobserver(bt.observers.BuySell)

    ALPHA_APIKEY = "3XBEGZUXVYMVD9NM"

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))


    # df2 = pd.read_csv("./datas/coin/BTCUSDT.csv",
    #                   parse_dates=True, index_col=0)
    filename = "./datas/coin/RM/BTCUSDT.csv"
    # df2 = pd.read_csv(filename, parse_dates=True, index_col=1)
    df2 = pd.read_csv(filename, parse_dates=True, index_col=0)
    # df2 = df2["2018-03-01":]
    df2 = df2["2019-01-02":]

    mons = (df2.index[-1] - df2.index[0]) / np.timedelta64(1, 'M')
    mons = int(round(mons, 0))
    initialcash = 100000.0

    # df2 = df2[:"2021-04-12"]
    # df2 = df2[['open', 'high', 'low', 'close', 'Volume']]
    # format = '%Y-%m-%d %H:%M:%S'
    # df2.index = df2.index.strftime(format)

    data1 = bt.feeds.PandasData(dataname=df2)

    cerebro.adddata(data1)

    # cerebro.replaydata(data1, timeframe=bt.TimeFrame.Minutes, compression=60)
    # Upsampleing data
    # cerebro.replaydata(data1, timeframe = bt.TimeFrame.Days, compression = 1)

    # Analyzer
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="mysharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="mdd")

    # Set our desired cash start
    cerebro.broker.setcash(initialcash)

    # Add a FixedSize sizer according to the stake
    # cerebro.addsizer(bt.sizers.PercentSizer, percents=92)

    # Set the commission - 0.1% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.001)

    # Print out the starting conditions
    # print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    thestrats = cerebro.run(maxcpus=6)
    thestrat = thestrats[0]

    fv = 0
    marginfv = 0

    if 'buyHist' in dir(thestrat):
        bh = thestrat.buyHist
        print("Final Profit of RSI Buy strategy : {:2f}, Net {:2f}".format(
            thestrat.finalProfit, thestrat.finalProfitNet))
        print("Init Value: {}, Out Value: {:.2f}, Net Value: {:.2f}, Interest Expense: {:.2f}".format(thestrat.buyHist['InitValue'].count(
        )*10000, thestrat.buyHist['OutValue'].sum(), thestrat.buyHist['NetValue'].sum(), (thestrat.buyHist['OutValue'] - thestrat.buyHist['NetValue']).sum()))
        marginfv = fv = thestrat.buyHist['NetValue'].sum()
        fv = thestrat.buyHist['PureOutValue'].sum()
        profit_margin = thestrat.finalProfit
        profit = thestrat.finalProfitPure
        initialcash = thestrat.buyHist['InitValue'].count()*10000

    print("Sharpe Ratio:", thestrat.analyzers.mysharpe.get_analysis())
    print("Max Draw Down: %.2f" %
          ((thestrat.analyzers.mdd.get_analysis()).max.drawdown))
    # Print out the final result
    print("Ticker : %s" % filename)
    print("InitValue : ", initialcash)
    if 'buyHist' in dir(thestrat):
        print("Final Portfolio Value: %.2f , %.2f percent (Pure: %.2f , %.2f %%)" %
              (marginfv, thestrat.finalProfit, fv, thestrat.finalProfitPure))
        cagr_margin = ((marginfv/initialcash)**(1/mons)-1)*100
        cagr = ((fv / initialcash) ** (1 / mons) - 1)*100
        print("CAGR(Month) : %.2f %% (Pure : %.2f %%)" % (cagr_margin, cagr))
    else:
        profit = (cerebro.broker.getvalue()/initialcash)*100-100
        print("Final Portfolio Value: %.2f , %.2f percent" %
              (cerebro.broker.getvalue(), profit))
        cagr = ((cerebro.broker.getvalue()/initialcash)**(1/mons)-1)*100
        print("CAGR(Month) : %.2f %%" % cagr)

    # Plotting incredibly is a line operation

    cerebro.plot(iplot=False)

    # cf.go_offline(connected=True)

    # b = Bokeh(style="bar")
    # cerebro.plot(b, iplot=False)

    # py.offline.plot_mpl(result[0][0], filename="simple_candlestick.html")
    # plotly.offline.plot_mpl(result[0][0], filename="simple_candlestick.html")
    # pio.write_html(result[0][0], file="hello_world.html", auto_open=True)

    # time.sleep(5)
    # cerebro = bt.Cerebro(stdstats=False)
    # cerebro.addstrategy(sc.RSIMomentum, printLog=True)
    # cerebro.addobserver(bt.observers.Value)
    # cerebro.addobserver(bt.observers.Trades)
    # cerebro.addobserver(bt.observers.BuySell)
    #
    # df2 = pd.read_csv("./datas/coin/BTCUSDT.csv",
    #                   parse_dates=True, index_col=0)
    # data1 = bt.feeds.PandasData(dataname=df2)
    # cerebro.adddata(data1)
    #
    # thestrats = cerebro.run(maxcpus=1)
    # thestrat = thestrats[0]
    # print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())
