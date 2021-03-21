# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from __future__ import absolute_import, division, print_function, unicode_literals

import pandas as pd
from pandas_datareader import data as web

import numpy
import argparse
import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

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

if __name__ == "__main__":
    # Create a cerebro entity
    cerebro = bt.Cerebro(stdstats=False)

    # Add a strategy
    cerebro.addstrategy(sc.RSIMomentum, printLog=True)
    # strats = cerebro.optstrategy(
    #     sc.MyFirstStrategy,
    #     momentumLasting=range(5,6),
    #     expectedProfit =numpy.arange(0.01, 0.04, 0.01)
    # )

    cerebro.addobserver(bt.observers.Value)
    cerebro.addobserver(bt.observers.Trades)
    cerebro.addobserver(bt.observers.BuySell)

    ALPHA_APIKEY = "3XBEGZUXVYMVD9NM"

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = (
        # os.path.join(os.environ['CONDA_PREFIX'], 'datas/AAPL.csv')
        "./datas/AAPL.csv"
    )

    df2 = pd.read_csv("./datas/btc_1H_kaggle.csv",
                      parse_dates=True, index_col=0)
    df2 = df2["2020-03-01":]
    # df2 = df2[:"2020-03-19"]
    data1 = bt.feeds.PandasData(dataname=df2)

    cerebro.adddata(data1)
    # cerebro.replaydata(data1, timeframe=bt.TimeFrame.Minutes, compression=60)

    # Upsampleing data
    # cerebro.replaydata(data1, timeframe = bt.TimeFrame.Days, compression = 1)

    # Analyzer
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="mysharpe")

    # Set our desired cash start
    cerebro.broker.setcash(100000.0)

    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.PercentSizer, percents=90)

    # Set the commission - 0.1% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.001)

    # Print out the starting conditions
    # print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    thestrats = cerebro.run(maxcpus=1)
    thestrat = thestrats[0]

    print("Sharpe Ratio:", thestrat.analyzers.mysharpe.get_analysis())
    # Print out the final result
    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # Plotting incredibly is a line operation

    # cerebro.plot(iplot=False)

    # cf.go_offline(connected=True)
    b = Bokeh(style="bar")
    cerebro.plot(b, iplot=False)
    # py.offline.plot_mpl(result[0][0], filename="simple_candlestick.html")
    # plotly.offline.plot_mpl(result[0][0], filename="simple_candlestick.html")
    # pio.write_html(result[0][0], file="hello_world.html", auto_open=True)
