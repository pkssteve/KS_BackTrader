# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from __future__ import absolute_import, division, print_function, unicode_literals

import pandas as pd
import os
from pandas_datareader import data as web

import numpy as np
import argparse
import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import time
import talib
import matplotlib.pyplot as plt

MACD_FAST_PERIOD = 14
MACD_SLOW_PERIOD = 21

def adjustPositionRatio(curRatio, direction):
    if direction == 1:
        curRatio += 0.2
        curRatio = min(curRatio, 0.8)
    else:
        curRatio -= 0.2
        curRatio = max(curRatio, 0.2)

    return curRatio

def resampleCandle(df, str):
    tempdf = df[["Open"]].resample(str).first().copy()
    tempdf[["High"]] = df[["High"]].resample(str).max().copy()
    tempdf[["Low"]] = df[["Low"]].resample(str).min().copy()
    tempdf[["Close"]] = df[["Close"]].resample(str).last().copy()
    tempdf[["Volume"]] = df[["Volume"]].resample(str).sum().copy()
    return tempdf

if __name__ == "__main__":

    basedir = "./datas/coin/future"
    fileBTC1hour = "./datas/coin/RM/BTCUSDT.csv"
    # basedir = "./datas/KOSDAQ"
    copydir = "./datas/coin/RM_D"
    listdf = []
    btc =pd.DataFrame()
    mdf=pd.DataFrame()
    mdf_H = pd.DataFrame()
    tickerCnt = 0

    start_date = "2020-03-01"
    end_date = "2021-03-30"

    hourstr = "00:00:00"
    btc1h = pd.read_csv(fileBTC1hour, parse_dates=True)
    btc1h = btc1h[btc1h['Datetime'].str.contains(hourstr)]
    btc1h.index = range(0, len(btc1h))

    coinprofit = {}

    with os.scandir(basedir) as entries:
        for f in entries:
            filename = basedir + '/' + f.name
            coinname = f.name.split('.')[0]
            if "DS_Store" in filename:
                continue

            # temp = pd.read_csv(filename, parse_dates=True, index_col=0)
            # if temp[temp.isna()]['Open'].count() != 0:
            #     continue
            # retemp = resampleCandle(temp, 'D')
            # retemp = retemp.fillna(method='ffill')
            # retemp.to_csv(copydir+'/'+coinname+'_D.csv')

            # temp = pd.read_csv(filename, parse_dates=True)

            print(filename)
            temp = pd.read_csv(filename, parse_dates=True)
            temp[['Name']] = coinname


            coinprofit[coinname] = []

            if (datetime.datetime.strptime(temp.loc[0,'Datetime'], "%Y-%m-%d") <= datetime.datetime.strptime(start_date, "%Y-%m-%d") and \
                    datetime.datetime.strptime(temp.loc[len(temp)-1, 'Datetime'], "%Y-%m-%d") > datetime.datetime.strptime(end_date, "%Y-%m-%d")):
                temp = temp[temp['Datetime'] >= start_date]
                temp = temp[temp['Datetime'] <= end_date]
                temp.index = range(0, len(temp))
                if "BTCUSDT" in coinname:
                    btc = temp.copy()
                mdf = pd.concat([mdf, temp])
                listdf.append(temp.copy())
                tickerCnt += 1

    macd, macd_s, macd_hist = talib.MACDEXT(btc['Close'], fastperiod=3, fastmatype=talib.MA_Type.EMA, slowperiod=10, slowmatype=talib.MA_Type.EMA, signalmatype=talib.MA_Type.EMA, signalperiod = 2)

    btc['macd'] = macd
    btc['macd_s'] = macd_s
    linecnt = 0
    position = 0
    longlist = {}


    buycash = 0
    port_value = 0

    numStocks = 5
    backwatch_days = 9
    selldelay =0 # position holding zero based value
    stepcnt = 0

    init_cash = 7000
    invest_cash = init_cash
    unitbuy = init_cash / numStocks
    final_value = init_cash
    max_cash = init_cash
    mdd = 0
    commision = 0.001
    leverage = 2.5
    ratio = 0.90
    interest = 0.0015
    interest_freq = 24

    doShortTrade = 0
    callCount = 0

    vdf = pd.DataFrame()

    for i in range(0, len(btc)):

        if i > len(btc[btc['macd'].isna()]) + backwatch_days:
            curdate = btc.iloc[i, 0]
            if pd.isna(btc.loc[i, 'macd']) == True:
                continue

            datetype = datetime.datetime.strptime(curdate, "%Y-%m-%d")
            pastdatetype = datetype - datetime.timedelta(days=backwatch_days)
            predatetype = datetype - datetime.timedelta(days=1)
            pastdate = datetime.datetime.strftime(pastdatetype, "%Y-%m-%d")

            # if predatetype.month != datetype.month:
            #     print(datetype.strftime("%Y-%m-%d"))
            #     init_cash += invest_cash
            #     final_value = final_value + invest_cash
            #     unitbuy = (final_value / numStocks) * ratio


            ## get close price in target old/cur datetime
            curClose = mdf[mdf['Datetime'] == curdate][['Close', 'Name']].copy()
            curClose.index = range(0, len(curClose))
            curOpen = mdf[mdf['Datetime'] == curdate][['Open', 'Name']].copy()
            curOpen.index = range(0, len(curOpen))
            pastClose = mdf[mdf['Datetime'] == pastdate][['Close', 'Name']].copy()
            pastClose.index = range(0, len(pastClose))
            curLow = mdf[mdf['Datetime'] == curdate][['Low', 'Name']].copy()
            curLow.index = range(0, len(curLow))
            curHigh = mdf[mdf['Datetime'] == curdate][['High', 'Name']].copy()
            curHigh.index = range(0, len(curHigh))
            # curClose_H = mdf_H[mdf_H['Datetime'] == (curdate + " " + hourstr)][['Close', 'Name']].copy()

            ## merge for diff rate caculation and descending sort by diff rate
            mclose = pd.merge(curClose, pastClose, how='left', on='Name')
            mclose2 = pd.merge(curOpen, pastClose, how='left', on='Name')
            mclose[['Diff']] = (mclose['Close_x']-mclose['Close_y'])/ mclose['Close_y']
            mclose2[['Diff']] = (mclose2['Open']-mclose2['Close'])/ mclose2['Close']
            mclose_p = mclose.sort_values(by=['Diff'], axis=0, ascending=False).copy()
            mclose_m = mclose.sort_values(by=['Diff'], axis=0, ascending=True).copy()

            mclose_p2 = mclose2.sort_values(by=['Diff'], axis=0, ascending=False).copy()
            mclose_m2 = mclose2.sort_values(by=['Diff'], axis=0, ascending=True).copy()



            # buy
            if position == 0:
                cdf = btc.loc[i - 30:i - 1, 'Close']
                cdf = cdf.append(pd.Series(btc1h[btc1h['Datetime'] == curdate + " " + hourstr]['Close']),
                                 ignore_index=True)
                macd2, macd_s2, macd_hist2 = talib.MACDEXT(cdf, fastperiod=7, fastmatype=talib.MA_Type.EMA,
                                                           slowperiod=14, slowmatype=talib.MA_Type.EMA,
                                                           signalmatype=talib.MA_Type.EMA, signalperiod=9)

                if macd2.iloc[-1] > macd_s2.iloc[-1] :  # last macd, macd signal
                    # and btc.loc[i, 'macd'] > btc.loc[i-1, 'macd']:
                    longlist = {}
                    shortlist = {}
                    for j in range(0, numStocks):
                        # if mclose_p2.iloc[j]['Diff'] > 0:
                        longlist[mclose_p2.iloc[j]['Name']] = curOpen[curOpen['Name']==mclose_p2.iloc[j]['Name']].iloc[0,0]

                    if len(longlist)>0:
                        position = 1
                        stepcnt = selldelay
                elif doShortTrade == 1:
                    longlist = {}
                    shortlist = {}
                    for j in range(0,numStocks):
                        shortlist[mclose_m2.iloc[j]['Name']] = \
                        curOpen[curOpen['Name'] == mclose_m2.iloc[j]['Name']].iloc[0, 0]

                    if len(shortlist) > 0:
                        position = 1
                        stepcnt = selldelay

            ## make coin list for long position
            if position == 1 and stepcnt == 0:

                ## calc sell results
                buycash = 0
                port_value = 0


                for key, val in longlist.items():
                    buycash += unitbuy
                    cur_price = curClose[curClose['Name'] == key].iloc[0, 0]
                    profit = (cur_price - val) / val
                    result_value = unitbuy + ((unitbuy * leverage) *profit)
                    result_value = max(result_value, 0)
                    lowprice = curLow[curLow['Name'] == key].iloc[0, 0]
                    curmdd = (lowprice - val) / val
                    curmdd = curmdd *leverage
                    if curmdd <= -0.8:
                        result_value = unitbuy * 0.2
                        callCount += 1



                    port_value += result_value

                    coinprofit[key].append(result_value)

                if doShortTrade==1:
                    for key, val in shortlist.items():

                        buycash += unitbuy
                        cur_price = curClose[curClose['Name'] == key].iloc[0, 0]
                        profit = (val - cur_price) / val
                        result_value = unitbuy + ((unitbuy * leverage) *profit)
                        result_value = max(result_value, 0)
                        highprice = curHigh[curHigh['Name'] == key].iloc[0, 0]
                        curmdd = (highprice - val) / val
                        curmdd = curmdd * leverage
                        if curmdd >= 0.8:
                            result_value = unitbuy * 0.2
                            callCount += 1

                        port_value += result_value
                        coinprofit[key].append(result_value)

                pre_fv = final_value
                final_value = (final_value - buycash) - ((buycash * leverage) * commision)
                final_value = (final_value + port_value) - ((port_value * leverage) * commision)
                final_value = final_value - ((buycash*(leverage-1))*interest)
                max_cash = max(final_value, max_cash)
                curdd = ((final_value - max_cash) / max_cash) * 100
                if curdd < mdd:
                    mdd_date = curdate
                    mdd_value = final_value
                mdd = min(mdd, curdd)

                # if pre_fv * 0.95 >= final_value:
                #     ratio = adjustPositionRatio(ratio, 0)
                # elif pre_fv * 1.05 <= final_value:
                #     ratio = adjustPositionRatio(ratio, 1)

                unitbuy = (final_value / numStocks) * ratio

                # save result
                vdf = vdf.append(pd.DataFrame(
                    {'Datetime':curdate,'Buy': buycash, 'Evaluation': port_value, 'Profit': (port_value - buycash) / buycash,
                     'PortValue': final_value}, index=[curdate]))

                # init position
                position = 0

            stepcnt -= 1
            stepcnt = max(stepcnt, 0)


    # detailed result for each coin
    iter = 0
    listdf=[]
    for key, value in coinprofit.items():
        dic = {key:value}
        listdf.append(pd.DataFrame.from_dict(dic))
        listdf[iter]['Profit'] = (listdf[iter][key]-unitbuy)/unitbuy
        iter += 1

    for df in listdf:
        if len(df)>0:
            cname = df.columns[0]
            close = float(curClose[curClose['Name']==cname]['Close'])
            observation  = len(df)
            numPlus = len(df[df['Profit']>0])
            win_rate = (numPlus/observation)*100
            totalPlus = df[df['Profit'] > 0]['Profit'].sum()
            totalMinus = df[df['Profit'] < 0]['Profit'].sum()
            totalcash = observation * unitbuy
            coin_earning_rate = ((df[cname].sum() - totalcash)/ unitbuy)

            print("[%s] Trades: %d, Price: %.4f, win rate: %.1f%%, +: %.1f%%, -: %.1f%%, Profit: %.2f%%" %
                  (cname, observation, close, win_rate, totalPlus*100, totalMinus*100, coin_earning_rate *100))

    fig =  plt.figure()
    ax1 = fig.add_subplot(311)
    ax2 = fig.add_subplot(312, sharex=ax1)
    ax3 = fig.add_subplot(313, sharex=ax1)
    vdf = btc.merge(vdf, how='outer', on='Datetime')
    btc[['Close', 'Datetime']].plot(ax=ax1)
    btc[['macd', 'macd_s']].plot(ax=ax2)
    vdf[['PortValue', 'Datetime']].plot('Datetime','PortValue', ax=ax3, marker='D', color='purple',markersize=3, linestyle='-', logy=True)

    ax1.legend(['BTC Price as reference'])
    ax2.legend(['BTC MACD', 'BTC MACD Signal'])
    ax3.legend(['Portfolio Value'])
    print("Init cash: %.2f, Final Value: %.2f, Profit: %.2f%%, MDD: %.1f" % (init_cash, final_value, ((final_value-init_cash)/init_cash)*100, mdd))
    print("Call count : %d" % callCount)
    print("MDD date : %s, MDD_PortValue : %.2f(%.2f%%)" % (mdd_date, mdd_value, ((mdd_value-init_cash)/init_cash)*100))
