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
import json

MACD_FAST_PERIOD = 14
MACD_SLOW_PERIOD = 21

def resampleCandle(df, str):
    tempdf = df[["Open"]].resample(str).first().copy()
    tempdf[["High"]] = df[["High"]].resample(str).max().copy()
    tempdf[["Low"]] = df[["Low"]].resample(str).min().copy()
    tempdf[["Close"]] = df[["Close"]].resample(str).last().copy()
    tempdf[["Volume"]] = df[["Volume"]].resample(str).sum().copy()
    return tempdf

def getTargetCandle(df, targetDT, listColumns, timeformat):
    strDT = targetDT.strftime(timeformat)
    targetdf = df[df['Datetime'] == strDT][listColumns]
    if len(targetdf) == 0:
        targetDT = targetDT - datetime.timedelta(days=1)
        targetdf = getTargetCandle(df, targetDT, listColumns, timeformat)

    targetdf.index = range(0, len(targetdf))
    targetdf = targetdf.copy()
    return targetdf

if __name__ == "__main__":

    # basedir = "./datas/coin/RM_D"
    basedir = "./datas/KOSDAQ_1D_4"
    copydir = "./datas/coin/RM_D"
    listdf = []
    btc =pd.DataFrame()
    mdf=pd.DataFrame()
    tickerCnt = 0

    start_date = "2010-03-05"
    end_date = "2017-04-30"

    coinprofit = {}


    with os.scandir(basedir) as entries:
        for f in entries:
            filename = basedir + '/' + f.name
            coinname = f.name.split('.')[0]

            if "DS_Store" in filename:
                continue

            # temp = pd.read_csv(filename, parse_dates=True, index_col=0)
            temp = pd.read_csv(filename, parse_dates=True)
            temp[['Name']] = coinname

            coinprofit[coinname] = []

            if (datetime.datetime.strptime(temp.loc[0,'Datetime'], "%Y-%m-%d") <= datetime.datetime.strptime(start_date, "%Y-%m-%d") and \
                    datetime.datetime.strptime(temp.loc[len(temp)-1, 'Datetime'], "%Y-%m-%d") > datetime.datetime.strptime(end_date, "%Y-%m-%d")):
                temp = temp[temp['Datetime'] >= start_date]
                temp = temp[temp['Datetime'] <= end_date]
                temp.index = range(0, len(temp))
                if "KOSDAQ" in coinname:
                    btc = temp.copy()
                mdf = pd.concat([mdf, temp])
                listdf.append(temp.copy())
                tickerCnt += 1

    macd, macd_s, macd_hist = talib.MACDEXT(btc['Close'], fastperiod=14, fastmatype=talib.MA_Type.EMA, slowperiod=21, slowmatype=talib.MA_Type.EMA, signalmatype=talib.MA_Type.EMA, signalperiod = 2)

    btc['macd'] = macd
    btc['macd_s'] = macd_s
    linecnt = 0
    position = 0
    position_day = 0
    longlist = {}

    unitbuy = 10000
    buycash = 0
    port_value = 0

    numStock = 10
    backwatch_days =1
    selldelay = 0 # position holding zero based value
    stepcnt = 0

    init_cash = 5000
    unitbuy = (init_cash / numStock)
    final_value = init_cash
    max_cash = init_cash
    mdd = 0
    commision = 0.001
    leverage = 1
    interest = 0.0015
    interest_freq = 24

    doShortTrade = 0

    start_cash = init_cash
    YoYReturn = pd.DataFrame()
    lastdt = datetime.datetime.strptime(start_date, "%Y-%m-%d")

    history = pd.DataFrame()
    monitor_date = "2016-08-01"

    vdf = pd.DataFrame()
    invalidCnt = 0
    for i in range(0, len(btc)):

        if i > len(btc[btc['macd'].isna()]) + 20:
            curdate = btc.iloc[i, 0]
            if pd.isna(btc.loc[i, 'macd']) == True:
                continue

            datetype = datetime.datetime.strptime(curdate, "%Y-%m-%d")
            pastdatetype = datetype - datetime.timedelta(days=backwatch_days)
            pastdate = datetime.datetime.strftime(pastdatetype, "%Y-%m-%d")
            predatedt = datetype - datetime.timedelta(days=1)
            predate = predatedt.strftime("%Y-%m-%d")

            if lastdt.year != datetype.year:
                pct = (final_value - start_cash) /start_cash
                YoYReturn = YoYReturn.append({"Year":predatedt.year, "Profit":pct}, ignore_index=True)
                start_cash = final_value


            ## get close price in target old/cur datetime
            curClose = mdf[mdf['Datetime'] == curdate][['Close', 'Name']].copy()
            curClose.index = range(0, len(curClose))
            curOpen = mdf[mdf['Datetime'] == curdate][['Open', 'Name']].copy()
            curOpen.index = range(0, len(curOpen))
            curHigh = mdf[mdf['Datetime'] == curdate][['High', 'Name']].copy()
            curHigh.index = range(0, len(curHigh))
            pastClose = getTargetCandle(mdf, pastdatetype, ['Datetime', 'Close', 'High', 'Low', 'Open','Name'], "%Y-%m-%d")
            pastClose.index = range(0, len(pastClose))
            preClose = getTargetCandle(mdf, predatedt, ['Datetime', 'Close', 'High', 'Low', 'Name'], "%Y-%m-%d")
            preClose.index = range(0, len(preClose))



            ## merge for diff rate caculation and descending sort by diff rate
            mclose = pd.merge(curClose, pastClose, how='left', on='Name')
            mclose2 = pd.merge(curOpen, pastClose, how='left', on='Name')
            mclose[['Diff']] = (pastClose['Close']-pastClose['Open']) / pastClose['Open']
            mclose2[['Diff']] = (mclose2['Open_x']-mclose2['Close']) / mclose2['Close']
            mclose_p = mclose.sort_values(by=['Diff'], axis=0, ascending=False).copy()
            mclose_m = mclose.sort_values(by=['Diff'], axis=0, ascending=True).copy()

            mclose_p2 = mclose2.sort_values(by=['Diff'], axis=0, ascending=False).copy()
            mclose_m2 = mclose2.sort_values(by=['Diff'], axis=0, ascending=True).copy()

            ## make coin list for long position
            if position == 1:
                targetdate = position_day + datetime.timedelta(days=selldelay+1)
                td_s = targetdate.strftime("%Y-%m-%d")

            if position == 1 and td_s <= curdate:

                ## calc sell results
                buycash = 0
                port_value = 0

                sellprices = []
                longlist = sorted(longlist.items())
                longlist = dict(longlist)
                for key, val in longlist.items():
                    buycash += unitbuy
                    if len(curOpen[curOpen['Name'] == key]) > 0:
                        cur_price = curOpen[curOpen['Name'] == key].iloc[0, 0]
                        profit = (cur_price - val) / val
                        result_value = unitbuy + (unitbuy * (profit * leverage))
                        result_value = max(result_value, 0)
                        port_value += result_value

                        sellprices.append(cur_price)
                    else:
                        invalidCnt += 1
                        result_value = unitbuy

                    coinprofit[key].append(result_value)

                if len(longlist):
                    trades_str = str(longlist)
                    history = history.append(
                        {"Date": curdate, "Trades": trades_str, "SellPrices": str(sellprices)}, ignore_index=True)


                if doShortTrade==1:
                    for key, val in shortlist.items():

                        buycash += unitbuy
                        if len(curOpen[curOpen['Name'] == key]) > 0:
                            cur_price = curOpen[curOpen['Name'] == key].iloc[0, 0]
                            profit = (val - cur_price) / val
                            result_value = unitbuy + (unitbuy * (profit * leverage))

                            result_value = max(result_value, 0)
                            port_value += result_value
                        else:
                            invalidCnt += 1
                            result_value = unitbuy

                        coinprofit[key].append(result_value)

                final_value = (final_value - buycash) - ((buycash * leverage) * commision)
                final_value = (final_value + port_value) - ((port_value * leverage) * commision)
                final_value = final_value - ((buycash*(leverage-1))*interest)
                max_cash = max(final_value, max_cash)
                curdd = ((final_value - max_cash) / max_cash) * 100
                if curdd < mdd:
                    mdd_date = curdate
                mdd = min(mdd, curdd)

                unitbuy = (final_value / numStock) * 0.8
                # unitbuy = (final_value / (numStock/2)) * 0.8

                # save result
                vdf = vdf.append(pd.DataFrame(
                    {'Datetime':curdate,'Buy': buycash, 'Evaluation': port_value, 'Profit': (port_value - buycash) / buycash,
                     'PortValue': final_value}, index=[curdate]))

                # init position
                position = 0

            # buy
            if position == 0:
                if True or btc.loc[i, 'macd'] > btc.loc[i, 'macd_s']:
                    # and btc.loc[i, 'macd'] > btc.loc[i - 1, 'macd']:
                    longlist = {}
                    shortlist = {}
                    for j in range(0, 20):
                        stockname = mclose_p.iloc[j]['Name']
                        curopen = curOpen[curOpen['Name'] == stockname].iloc[0, 0]
                        curhigh = curHigh[curHigh['Name'] == stockname].iloc[0, 0]
                        curclose = curClose[curClose['Name'] == stockname].iloc[0, 0]
                        prehigh = pastClose[pastClose['Name'] == stockname].iloc[0]['High']
                        prelow = pastClose[pastClose['Name'] == stockname].iloc[0]['Low']
                        pregap = prehigh - prelow

                        if curhigh == curopen:
                            continue
                        # ibs = (curclose-curopen)/(curhigh-curopen)
                        # if ibs <= 0.3:
                        if curopen + pregap < curhigh:
                            longlist[stockname] = curopen + pregap

                        if len(longlist) == numStock:
                            break


                    if len(longlist) > 0:
                        position = 1
                        position_day = datetime.datetime.strptime(curdate, "%Y-%m-%d")
                        stepcnt = selldelay

                    if monitor_date == datetype.strftime("%Y-%m-%d"):
                        mclose_p.to_csv("diff_1d.csv")
                        # exit()

                elif doShortTrade == 1:
                    longlist = {}
                    shortlist = {}
                    for j in range(5, 5+ numStock):
                        stockname =mclose_m.iloc[j]['Name']
                        shortlist[stockname] = \
                            curClose[curClose['Name'] == stockname].iloc[0, 0]

                    position = 1
                    position_day = datetime.datetime.strptime(curdate, "%Y-%m-%d")
                    stepcnt = selldelay

            lastdt = datetype

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

    # for df in listdf:
    #     if len(df)>0:
    #         cname = df.columns[0]
    #         close = float(curClose[curClose['Name']==cname]['Close'])
    #         observation  = len(df)
    #         numPlus = len(df[df['Profit']>0])
    #         win_rate = (numPlus/observation)*100
    #         totalPlus = df[df['Profit'] > 0]['Profit'].sum()
    #         totalMinus = df[df['Profit'] < 0]['Profit'].sum()
    #         totalcash = observation * unitbuy
    #         coin_earning_rate = ((df[cname].sum() - totalcash)/ unitbuy)
    #
    #         print("[%s] Trades: %d, Price: %.4f, win rate: %.1f%%, +: %.1f%%, -: %.1f%%, Profit: %.2f%%" %
    #               (cname, observation, close, win_rate, totalPlus*100, totalMinus*100, coin_earning_rate *100))

    pct = (final_value - start_cash) / start_cash
    if datetype is not None:
        YoYReturn = YoYReturn.append({"Year": datetype.year, "Profit": pct}, ignore_index=True)


    start_date_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    years = max(1,int((end_date_dt - start_date_dt).days/365))
    cagr = ((final_value / init_cash) ** (1 / years) - 1) * 100

    fig =  plt.figure()
    fig.suptitle('KOSDAQ Momentum Strategy - trades %d stocks everyday' % (numStock), fontsize=15)
    ax1 = fig.add_subplot(311)
    ax2 = fig.add_subplot(312, sharex=ax1)
    ax3 = fig.add_subplot(313, sharex=ax1)
    subtitle = "Profit %.1f%%, CAGR %.1f%% MDD %.1f%% in %s ~ %s" % (((final_value-init_cash)/init_cash)*100, cagr, abs(mdd), start_date, end_date)
    ax1.set_title(subtitle)
    ax3.set_title("Leverage x %d" % leverage)
    vdf2 = btc.merge(vdf, how='left', on='Datetime')
    btc[['Close', 'Datetime']].plot(ax=ax1)
    btc[['macd', 'macd_s']].plot(ax=ax2)
    vdf2.plot('Datetime','PortValue', ax=ax3, marker='D', color='purple',markersize=3, linestyle='-', title='')



    ax1.legend(['KOSDAQ Index'])
    ax2.legend(['KOSDAQ MACD', 'KOSDAQ MACD Signal'])
    ax3.legend(['Portfolio Value'])
    print("Init cash: %.2f, Final Value: %.2f, Profit: %.2f%%, CAGR: %.2f%% MDD: %.1f%%" % (init_cash, final_value, ((final_value-init_cash)/init_cash)*100, cagr, mdd))
    print("Invalid Count:%d, Backwatch day:%d, Stock Number:%d, Sell Delay:%d" % (invalidCnt, backwatch_days, numStock, selldelay))
    print("MDD Date %s" % mdd_date)