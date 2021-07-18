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
import json
from collections import deque

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
    listTime = [" 09:00:00", " 10:00:00", " 11:00:00", " 12:00:00", " 13:00:00", " 14:00:00", " 15:00:00"]
    step = 0
    totalticks = len(listTime)
    for i in range(len(df)):
        if step % totalticks == 0:
            curdt = df.iloc[i, 0]
        if step % totalticks > 0 and curdt != df.iloc[i, 0]:
            step += totalticks - (step % totalticks)
            curdt = df.iloc[i, 0]
        df.iloc[i, 0] = df.iloc[i, 0] + listTime[step % totalticks]
        step += 1

    df.to_csv(destdir + '/' + filename, index=None)



if __name__ == "__main__":

    # basedir = "./datas/coin/RM_D"
    basedir = "./datas/KOSDAQ_1H_2"
    basedir2 = "./datas/KOSDAQ_1D_3"
    copydir = "./datas/KOSDAQ_1H"
    listdf = []
    btc = pd.DataFrame()
    btc2 = pd.DataFrame()
    mdf = pd.DataFrame()
    mdf2 = pd.DataFrame()
    tickerCnt = 0

    start_date = "2019-03-05"
    end_date = "2020-04-10"

    coinprofit = {}

    with os.scandir(basedir) as entries:
        for f in entries:
            filename = basedir + '/' + f.name
            coinname = f.name.split('.')[0]
            if "DS_Store" in filename:
                continue

            temp = pd.read_csv(filename, parse_dates=True)
            # exportAppendedTime(temp, basedir + '_2', f.name)
            # continue
            # temp.to_csv("./datas/KOSDAQ_1D_4/"+coinname+".csv", index=0)
            # continue

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

    numStock = 5
    unitbuy = 10000
    buycash = 0
    port_value = 0

    backwatch_days = 14
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

    uppercount = 0

    targetH = "15:00:00"
    print("Trigger Hour: %s" % targetH)
    cond_num = -1

    boughtStockLong = 0

    history = pd.DataFrame()
    monitor_date = "2016-08-01"

    vdf = pd.DataFrame()
    invalidCnt = 0

    upperprice = pd.DataFrame()
    upperprice_sum = pd.DataFrame()
    listTime = ["09:00:00", "10:00:00", "11:00:00", "12:00:00", "13:00:00", "14:00:00", "15:00:00"]
    staydf = pd.DataFrame()
    unitcash = 1000

    for i in range(0, len(btc)):

        if i > (len(btc2[btc2['macd'].isna()])*4) + CALC_MARGIN + backwatch_days*2:
            curdate = btc.iloc[i, 0]
            if pd.isna(btc.loc[i, 'macd']) == True:
                continue


            datetype = datetime.datetime.strptime(curdate, "%Y-%m-%d %H:%M:%S")
            pastdatetype = datetype - datetime.timedelta(days=backwatch_days)
            pastdate = datetime.datetime.strftime(pastdatetype, "%Y-%m-%d %H:%M:%S")
            predatedt = datetype - datetime.timedelta(days=1)
            predate = predatedt.strftime("%Y-%m-%d %H:%M:%S")
            day_str = datetype.strftime("%Y-%m-%d")
            hour_str = datetype.strftime("%H:%M:%S")


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
            curHigh = mdf[mdf['Datetime'] == curdate][['High', 'Name', 'Datetime']].copy()
            curHigh.index = range(0, len(curHigh))
            curVol = mdf[mdf['Datetime'] == curdate][['Volume', 'Name', 'Datetime']].copy()
            curVol.index = range(0, len(curVol))

            # pastClose = getTargetCandle(mdf, pastdatetype, ['Close', 'Name'], "%Y-%m-%d %H:%M:%S")
            pastClose2 = getTargetCandle(mdf2, pastdatetype, ['Close', 'Name'], "%Y-%m-%d")
            preCloseDay = getTargetCandle(mdf2, predatedt, ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Name'], "%Y-%m-%d")
            curCandleDay = getTargetCandle(mdf2, datetype, ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Name'], "%Y-%m-%d")


            ## merge for diff rate caculation and descending sort by diff rate
            mclose = pd.merge(curClose, pastClose2, how='left', on='Name')
            # mclose2 = pd.merge(curOpen, pastClose2, how='left', on='Name')
            mclose[['Diff']] = (mclose['Close_x']-mclose['Close_y']) / mclose['Close_y']
            # mclose2[['Diff']] = (mclose2['Open']-mclose2['Close']) / mclose2['Close']
            mclose_p = mclose.sort_values(by=['Diff'], axis=0, ascending=False).copy()
            mclose_m = mclose.sort_values(by=['Diff'], axis=0, ascending=True).copy()
            # mclose_p2 = mclose2.sort_values(by=['Diff'], axis=0, ascending=False).copy()
            # mclose_m2 = mclose2.sort_values(by=['Diff'], axis=0, ascending=True).copy()

            btc2_t = btc2[btc2['Datetime'] == datetype.strftime("%Y-%m-%d")].copy()
            btc2_t.index = range(0, len(btc2_t))

            upperstocks = mclose[mclose['Diff'] >= 0.295].copy()
            uppercount = len(upperstocks)
            upperprice_sum = upperprice_sum.append({"Date": day_str, "Time": hour_str, "Count": uppercount},
                                           ignore_index=True)
            for i in range(len(upperstocks)):
                upperprice = upperprice.append({"Date":day_str, "Time":hour_str, "Stock":upperstocks.iloc[i,1], "Diff":upperstocks.iloc[i,4], "Close":upperstocks.iloc[i,0]}, ignore_index=True)



            # staydf = pd.DataFrame()
            # dates = upperprice.drop_duplicates(['Date'])['Date']
            # for date in dates:
            #     df = upperprice[upperprice['Date']==date]
            #     stocks = df.drop_duplicates(['Stock'])['Stock']
            #     for stock in stocks:
            #         staycount = len(df[(df['Time']=='13:00:00') & (df['Stock']==stock)])
            #         isfinal = len(df[(df['Time']=='15:00:00') & (df['Stock']==stock)])
            #         staydf = staydf.append({"Stock":stock, "Stay":staycount, "Final":isfinal}, ignore_index=True)


            ## make coin list for long position
            if position == 1:
                targetdate = position_day + datetime.timedelta(days=selldelay)
                td_s = targetdate.strftime("%Y-%m-%d 00:00:00")

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
                        # cur_price = curClose[curClose['Name'] == key].iloc[0, 0]
                        cur_price = curOpen[curOpen['Name'] == key].iloc[0, 0]  # 1 is open

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
                    history = history.append({"Date":curdate, "Trades":trades_str, "SellPrices":str(sellprices)}, ignore_index=True)
                else:
                    pass

                # if len(staydf) > 0:
                #     for i in range(0, len(staydf)):
                #         stock = staydf.loc[i, 'Stock']
                #         if len(curOpen[curOpen['Name'] == stock]) > 0:
                #             buycash += unitbuy
                #             stock = staydf.loc[i, 'Stock']
                #             close = staydf.loc[i, 'Close']
                #
                #             cur_price = curOpen[curOpen['Name'] == stock].iloc[0, 0]  # 1 is open
                #             profit = (cur_price - close) / close
                #             result_value = unitbuy + (unitbuy * (profit * leverage))
                #             result_value = max(result_value, 0)
                #             port_value += result_value





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

                unitbuy = int (final_value // numStock)

                # save result
                if buycash != 0:
                    vdf = vdf.append(pd.DataFrame(
                        {'Datetime':curdate,'Buy': buycash, 'Evaluation': port_value, 'Profit': (port_value - buycash) / buycash,
                         'PortValue': final_value}, index=[curdate]))

                # init position
                position = 0
                position_day = 0
                longlist = {}
                shortlist = {}
                boughtStockLong = 0
                staydf = pd.DataFrame()

            # buy
            if position_day == 0 and targetH == hour_str:
            # if position_day == 0 :
                if True or btc2_t.loc[0,'macd'] > btc2_t.loc[0,'macd_s']:

                    for j in range(5, len(mclose_p)):
                        if boughtStockLong < numStock:
                            stockname = mclose_p.iloc[j]['Name']
                            # stockname = mclose_m.iloc[j]['Name']
                            # if mclose_m.iloc[j]['Diff'] < 0.07:
                            #     continue
                            preCandle = preCloseDay[preCloseDay['Name']==stockname]
                            if len(preCandle)==0:
                                continue

                            preclose = preCandle['Close'].iloc[0]
                            curCandle = curCandleDay[curCandleDay['Name']==stockname]
                            pregap = preCandle['High'].iloc[0] - preCandle['Low'].iloc[0]
                            prerate = (preCandle['High'].iloc[0] - preCandle['Low'].iloc[0])/preCandle['Low'].iloc[0]
                            curOpenDay = curCandle['Open'].iloc[0]
                            curCloseHour = curClose[curClose['Name'] == stockname].iloc[0, 0]
                            curCandleOpen = curOpen[curOpen['Name'] == stockname].iloc[0, 0]
                            curHighHour = curHigh[curHigh['Name'] == stockname].iloc[0, 0]
                            vol = curVol[curVol['Name'] == stockname].iloc[0, 0]
                            prevol = int(preCandle['Volume'])
                            volratio = prevol/vol

                            if curCloseHour/preclose > 1.294:
                                uppercount += 1

                            # if True or volratio >= 1:
                            if (curCloseHour-preclose) > pregap * 0.5 and curCandleOpen < preclose + (pregap * 0.5)\
                                    and prerate >= 0.08:
                            # if (curHighHour-preclose) > pregap * 0.5 and curCandleOpen < preclose + (pregap * 0.5) and volratio > 1:
                            # if (curHighHour-preclose) > pregap * 0.5 and curCandleOpen < preclose + (pregap * 0.5):
                            # if (curHighHour-preclose) > pregap * 1 and curCandleOpen < preclose + (pregap * 1):
                            # if (curHighHour-preclose) > pregap * 1 and curCandleOpen < preclose + (pregap * 1) and volratio > 1:
                                longlist[stockname] = curCloseHour
                                # longlist[stockname] = (preclose + (pregap * 0.5))*1.01
                                boughtStockLong += 1
                                cond_num = 3
                        else:
                            break

                    if boughtStockLong > 0:
                        position = 1
                        position_day = datetime.datetime.strptime(curdate, "%Y-%m-%d %H:%M:%S")
                        stepcnt = selldelay

                        # if monitor_date == datetype.strftime("%Y-%m-%d"):
                        #     mclose_p.to_csv("diff_1h.csv")

                        # if hour_str == "15:00:00":
                        #     df = upperprice[upperprice['Date'] == day_str]
                        #     stocks = df.drop_duplicates(['Stock'])['Stock']
                        #     for stock in stocks:
                        #         df = df[df['Time']>="11:00:00"]
                        #         staycount = len(df[df['Stock'] == stock])
                        #         close = df[(df['Time'] == '15:00:00') & (df['Stock'] == stock)]['Close']
                        #         isfinal = len(df[(df['Time'] == '15:00:00') & (df['Stock'] == stock)])
                        #         if staycount == 5 and isfinal == 1:
                        #             staydf = staydf.append(
                        #                 {"Stock": stock, "Stay": staycount, "Final": isfinal, "Close": float(close)},
                        #                 ignore_index=True)





                elif doShortTrade == 1:
                    for j in range(0, 10):
                        shortlist[mclose_m.iloc[j]['Name']] = \
                            curOpen[curOpen['Name'] == mclose_m.iloc[j]['Name']].iloc[0, 0]

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
    print("Init cash: %.2f, Final Value: %.2f, Profit: %.2f, MDD: %.1f" % (init_cash, final_value, ((final_value-init_cash)/init_cash)*100, mdd))
    print("Invalid Count:%d, Backwatch day:%d, Stock Number:%d, Sell Delay:%d" % (invalidCnt, backwatch_days, numStock, selldelay))
    print("Condition number %d" % cond_num)