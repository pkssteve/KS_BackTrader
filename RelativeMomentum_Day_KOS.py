# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from __future__ import absolute_import, division, print_function, unicode_literals

import pandas as pd
import os
from pandas_datareader import data as web
import math

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
CALC_MARGIN = 24


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

    return targetdf

def exportAppendedTime(df, destdir, filename):
    listTime = [" 09:00:00", " 11:00:00", " 13:00:00", " 15:00:00"]
    step = 0

    for i in range(len(df)):
        if step % 4 == 0:
            curdt = df.iloc[i, 0]
        if step % 4 > 0 and curdt != df.iloc[i, 0]:
            step += 4 - (step % 4)
            curdt = df.iloc[i, 0]
        df.iloc[i, 0] = df.iloc[i, 0] + listTime[step % 4]
        step += 1

    df.to_csv(destdir + '/' + filename)



if __name__ == "__main__":

    # basedir = "./datas/coin/RM_D"
    basedir = "./datas/KOSDAQ_2H_Full2"
    basedir2 = "./datas/KOSDAQ_1D_Full"
    copydir = "./datas/KOSDAQ_2H_Full2"
    listdf = []
    btc = pd.DataFrame()
    btc2 = pd.DataFrame()
    mdf = pd.DataFrame()
    mdf2 = pd.DataFrame()
    tickerCnt = 0

    start_date = "2018-06-05"
    end_date = "2020-06-30"

    coinprofit = {}

    with os.scandir(basedir) as entries:
        for f in entries:
            filename = basedir + '/' + f.name
            coinname = f.name.split('.')[0]
            if "DS_Store" in filename:
                continue

            temp = pd.read_csv(filename, parse_dates=True, index_col=0)
            temp[['Name']] = coinname

            coinprofit[coinname] = []

            # if (datetime.datetime.strptime(temp.loc[0,'Datetime'], "%Y-%m-%d") <= datetime.datetime.strptime(start_date, "%Y-%m-%d") and \
            #         datetime.datetime.strptime(temp.loc[len(temp)-1, 'Datetime'], "%Y-%m-%d") > datetime.datetime.strptime(end_date, "%Y-%m-%d")):

            temp = temp[temp['Datetime'] >= start_date]
            temp = temp[temp['Datetime'] <= end_date]
            temp.index = range(0, len(temp))

            temp = temp.copy()

            if "KOSDAQ" in coinname:
                btc = temp.copy()
            mdf = pd.concat([mdf, temp])
            listdf.append(temp.copy())
            tickerCnt += 1


    with os.scandir(basedir2) as entries:
        for f in entries:
            filename = basedir2 + '/' + f.name
            coinname = f.name.split('.')[0]
            if "DS_Store" in filename:
                continue

            temp = pd.read_csv(filename, parse_dates=True, index_col=0)
            temp[['Name']] = coinname

            # if (datetime.datetime.strptime(temp.loc[0,'Datetime'], "%Y-%m-%d") <= datetime.datetime.strptime(start_date, "%Y-%m-%d") and \
            #         datetime.datetime.strptime(temp.loc[len(temp)-1, 'Datetime'], "%Y-%m-%d") > datetime.datetime.strptime(end_date, "%Y-%m-%d")):
            temp = temp[temp['Datetime'] >= start_date]
            temp = temp[temp['Datetime'] <= end_date]
            temp.index = range(0, len(temp))
            temp = temp.copy()
            if "KOSDAQ" in coinname:
                btc2 = temp.copy()
            mdf2 = pd.concat([mdf2, temp])


    macd, macd_s, macd_hist = talib.MACDEXT(btc['Close'], fastperiod=14, fastmatype=talib.MA_Type.EMA, slowperiod=21, slowmatype=talib.MA_Type.EMA, signalmatype=talib.MA_Type.EMA, signalperiod = 2)
    macd2, macd_s2, macd_hist2 = talib.MACDEXT(btc2['Close'], fastperiod=14, fastmatype=talib.MA_Type.EMA, slowperiod=21,
                                            slowmatype=talib.MA_Type.EMA, signalmatype=talib.MA_Type.EMA,
                                            signalperiod=2)

    btc['macd'] = macd
    btc['macd_s'] = macd_s
    btc2['macd'] = macd2
    btc2['macd_s'] = macd_s2
    linecnt = 0
    position = 0
    position_day = 0
    longlist = {}

    numStock = 100
    unitbuy = 10000
    buycash = 0
    port_value = 0

    backwatch_days =1
    selldelay = 1 # position holding zero based value
    stepcnt = 0

    init_cash = 150000
    final_value = init_cash
    max_cash = init_cash
    mdd = 0
    commision = 0.001
    leverage = 1
    interest = 0.0015
    interest_freq = 24

    doShortTrade = 0

    boughtStockLong = 0

    vdf = pd.DataFrame()
    invalidCnt = 0
    for i in range(0, len(btc)):

        if i > (len(btc2[btc2['macd'].isna()])*4) + CALC_MARGIN + backwatch_days:
            curdate = btc.iloc[i, 0]
            if pd.isna(btc.loc[i, 'macd']) == True:
                continue

            datetype = datetime.datetime.strptime(curdate, "%Y-%m-%d %H:%M:%S")
            pastdatetype = datetype - datetime.timedelta(days=backwatch_days)
            pastdate = datetime.datetime.strftime(pastdatetype, "%Y-%m-%d %H:%M:%S")
            predatedt = datetype - datetime.timedelta(days=1)
            predate = predatedt.strftime("%Y-%m-%d %H:%M:%S")

            tomodt = datetype + datetime.timedelta(days=1)
            tomodt_str = tomodt.strftime("%Y-%m-%d")

            btc2_t = btc2[btc2['Datetime'] == datetype.strftime("%Y-%m-%d")]
            if math.isnan(btc2_t['macd']):
                continue

            ## get close price in target old/cur datetime
            curClose = mdf[mdf['Datetime'] == curdate][['Close', 'Name', 'Datetime']].copy()
            curClose.index = range(0, len(curClose))
            curOpen = mdf[mdf['Datetime'] == curdate][['Open', 'Name', 'Datetime']].copy()
            curOpen.index = range(0, len(curOpen))
            # pastClose = getTargetCandle(mdf, pastdatetype, ['Close', 'Name'], "%Y-%m-%d %H:%M:%S")
            pastClose2 = getTargetCandle(mdf2, pastdatetype, ['Close', 'Name'], "%Y-%m-%d")
            preCloseDay = getTargetCandle(mdf2, predatedt, ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Name'], "%Y-%m-%d")
            curCandleDay = getTargetCandle(mdf2, datetype, ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Name'], "%Y-%m-%d")


            ## merge for diff rate caculation and descending sort by diff rate
            mclose = pd.merge(curClose, pastClose2, how='left', on='Name')
            mclose2 = pd.merge(curOpen, pastClose2, how='left', on='Name')
            mclose[['Diff']] = (mclose['Close_x']-mclose['Close_y']) / mclose['Close_y']
            mclose2[['Diff']] = (mclose2['Open']-mclose2['Close']) / mclose2['Close']
            mclose_p = mclose.sort_values(by=['Diff'], axis=0, ascending=False).copy()
            mclose_m = mclose.sort_values(by=['Diff'], axis=0, ascending=True).copy()

            mclose_p2 = mclose2.sort_values(by=['Diff'], axis=0, ascending=False).copy()
            mclose_m2 = mclose2.sort_values(by=['Diff'], axis=0, ascending=True).copy()

            btc2_t = btc2[btc2['Datetime'] == datetype.strftime("%Y-%m-%d")].copy()
            btc2_t.index = range(0, len(btc2_t))

            ## make coin list for long position
            if position == 1:
                targetdate = position_day + datetime.timedelta(days=selldelay)
                td_s = targetdate.strftime("%Y-%m-%d 00:00:00")

            if position == 1 and td_s <= curdate:

                ## calc sell results
                buycash = 0
                port_value = 0


                for key, val in longlist.items():
                    buycash += unitbuy
                    if len(curClose[curClose['Name'] == key]) > 0:
                        # cur_price = curClose[curClose['Name'] == key].iloc[0, 0]
                        cur_price = curCandleDay[curCandleDay['Name'] == key].iloc[0, 1]  # 1 is open
                        profit = (cur_price - val) / val
                        result_value = unitbuy + (unitbuy * (profit * leverage))
                        result_value = max(result_value, 0)
                        port_value += result_value
                    else:
                        invalidCnt += 1
                        result_value = unitbuy

                    coinprofit[key].append(result_value)

                if doShortTrade == 1:
                    for key, val in shortlist.items():

                        buycash += unitbuy
                        cur_price = curClose[curClose['Name'] == key].iloc[0, 0]
                        profit = (val - cur_price) / val
                        result_value = unitbuy + (unitbuy * (profit * leverage))

                        result_value = max(result_value, 0)
                        port_value += result_value

                        coinprofit[key].append(result_value)

                final_value = (final_value - buycash) - ((buycash * leverage) * commision)
                final_value = (final_value + port_value) - ((port_value * leverage) * commision)
                final_value = final_value - ((buycash*(leverage-1)) * interest)
                max_cash = max(final_value, max_cash)
                mdd = min(mdd, ((final_value - max_cash)/max_cash)*100)

                # save result
                vdf = vdf.append(pd.DataFrame(
                    {'Datetime':curdate,'Buy': buycash, 'Evaluation': port_value, 'Profit': (port_value - buycash) / buycash,
                     'PortValue': final_value}, index=[curdate]))

                # init position
                position = 0
                position_day = 0
                longlist = {}
                shortlist = {}
                boughtStockLong = 0

            # buy
            if position_day == 0 or (position_day != 0 and position_day.strftime("%Y-%m-%d") == datetype.strftime("%Y-%m-%d")):
            # if position_day == 0 :
                if btc2_t.loc[0,'macd'] > btc2_t.loc[0,'macd_s']:
                    if boughtStockLong < numStock:
                        for j in range(0, numStock):
                            longlist[mclose_p.iloc[j]['Name']] = \
                                curClose[curClose['Name'] == mclose_p.iloc[j]['Name']].iloc[0, 0]
                            boughtStockLong += 1

                        position = 1
                        position_day = datetime.datetime.strptime(curdate, "%Y-%m-%d %H:%M:%S")
                        stepcnt = selldelay


                elif doShortTrade == 1:
                    for j in range(0, 10):
                        shortlist[mclose_m2.iloc[j]['Name']] = \
                            curOpen[curOpen['Name'] == mclose_m2.iloc[j]['Name']].iloc[0, 0]

                    position = 1
                    position_day = datetime.datetime.strptime(curdate, "%Y-%m-%d %H:%M:%S")
                    stepcnt = selldelay

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

    start_date_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    years = max(1,int((end_date_dt - start_date_dt).days/365))
    cagr = ((final_value / init_cash) ** (1 / years) - 1) * 100

    fig =  plt.figure()
    ax1 = fig.add_subplot(311)
    ax2 = fig.add_subplot(312, sharex=ax1)
    ax3 = fig.add_subplot(313, sharex=ax1)
    vdf2 = btc.merge(vdf, how='left', on='Datetime')
    btc[['Close', 'Datetime']].plot(ax=ax1)
    btc[['macd', 'macd_s']].plot(ax=ax2)
    vdf2.plot('Datetime','PortValue', ax=ax3, marker='D', color='purple',markersize=3, linestyle='-')

    ax1.legend(['KOSDAQ Index as reference'])
    ax2.legend(['KOSDAQ MACD', 'KOSDAQ MACD Signal'])
    ax3.legend(['Portfolio Value'])
    print("Init cash: %.2f, Final Value: %.2f, Profit: %.2f, CAGR: %.2f MDD: %.1f" % (init_cash, final_value, ((final_value-init_cash)/init_cash)*100, cagr, mdd))
    print("Invalid Count:%d, Backwatch day:%d, Stock Number:%d, Sell Delay:%d" % (invalidCnt, backwatch_days, numStock, selldelay))