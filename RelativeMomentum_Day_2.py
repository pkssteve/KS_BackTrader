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

MACD_FAST_PERIOD = 14
MACD_SLOW_PERIOD = 21

def resampleCandle(df, str):
    tempdf = df[["Open"]].resample(str).first().copy()
    tempdf[["High"]] = df[["High"]].resample(str).max().copy()
    tempdf[["Low"]] = df[["Low"]].resample(str).min().copy()
    tempdf[["Close"]] = df[["Close"]].resample(str).last().copy()
    tempdf[["Volume"]] = df[["Volume"]].resample(str).sum().copy()
    return tempdf

if __name__ == "__main__":

    basedir = "./datas/coin/RM_D"
    copydir = "./datas/coin/RM_D"
    listdf = []
    btc =pd.DataFrame()
    mdf=pd.DataFrame()
    tickerCnt = 0

    start_date = "2019-01-30"
    end_date = "2019-12-30"

    coinprofit = {}

    with os.scandir(basedir) as entries:
        for f in entries:
            filename = basedir + '/' + f.name
            coinname = f.name.split('.')[0]

            # temp = pd.read_csv(filename, parse_dates=True, index_col=0)
            # if temp[temp.isna()]['Open'].count() != 0:
            #     continue
            # retemp = resampleCandle(temp, 'D')
            # retemp = retemp.fillna(method='ffill')
            # retemp.to_csv(copydir+'/'+coinname+'_D.csv')

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
                print(coinname)
                tickerCnt += 1

    macd, macd_s, macd_hist = talib.MACDEXT(btc['Close'], fastperiod=MACD_FAST_PERIOD, fastmatype=talib.MA_Type.EMA, slowperiod=MACD_SLOW_PERIOD, slowmatype=talib.MA_Type.EMA, signalmatype=talib.MA_Type.EMA)

    btc['macd'] = macd
    btc['macd_s'] = macd_s
    linecnt = 0
    position = 0
    longlist = {}

    unitbuy = 10000
    buycash = 0
    port_value = 0

    backwatch_days = 14
    selldelay =0 # position holding
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

    vdf = pd.DataFrame()

    for i in range(0, len(btc)):

        if i > len(btc[btc['macd'].isna()]) + 1:
            curdate = btc.iloc[i, 0]
            if pd.isna(btc.loc[i, 'macd']) == True:
                continue

            datetype = datetime.datetime.strptime(curdate, "%Y-%m-%d")
            pastdatetype = datetype - datetime.timedelta(days=backwatch_days)
            pastdate = datetime.datetime.strftime(pastdatetype, "%Y-%m-%d")


            ## get close price in target old/cur datetime
            curClose = mdf[mdf['Datetime'] == curdate][['Close', 'Name']].copy()
            curClose.index = range(0, len(curClose))
            curOpen = mdf[mdf['Datetime'] == curdate][['Open', 'Name']].copy()
            curOpen.index = range(0, len(curOpen))
            pastClose = mdf[mdf['Datetime'] == pastdate][['Close', 'Name']].copy()
            pastClose.index = range(0, len(pastClose))

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
                if btc.loc[i, 'macd'] > btc.loc[i, 'macd_s'] and btc.loc[i, 'macd'] > btc.loc[i-1, 'macd']:
                    longlist = {}
                    shortlist = {}
                    for j in range(0, 10):
                        longlist[mclose_p2.iloc[j]['Name']] = curOpen[curOpen['Name']==mclose_p2.iloc[j]['Name']].iloc[0,0]

                    position = 1
                    stepcnt = selldelay
                elif doShortTrade == 1:
                    longlist = {}
                    shortlist = {}
                    for j in range(0, 10):
                        shortlist[mclose_m2.iloc[j]['Name']] = \
                        curOpen[curOpen['Name'] == mclose_m2.iloc[j]['Name']].iloc[0, 0]

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
                    result_value = unitbuy + (unitbuy * (profit * leverage))
                    result_value = max(result_value, 0)
                    port_value += result_value

                    coinprofit[key].append(result_value)

                if doShortTrade==1:
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
                final_value = final_value - ((buycash*(leverage-1))*interest)
                max_cash = max(final_value, max_cash)
                mdd = min(mdd, ((final_value - max_cash)/max_cash)*100)

                # save result
                vdf = vdf.append(pd.DataFrame(
                    {'Buy': buycash, 'Evaluation': port_value, 'Profit': (port_value - buycash) / buycash,
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


    vdf['PortValue'].plot()
    print("Init cash: %.2f, Final Value: %.2f, Profit: %.2f, MDD: %.1f" % (init_cash, final_value, ((final_value-init_cash)/init_cash)*100, mdd))
