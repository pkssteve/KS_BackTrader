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

if __name__ == "__main__":

    basedir = "./datas/coin/RM"
    listdf = []
    mdf=pd.DataFrame()
    tickerCnt = 0

    start_date = "2019-12-30"
    end_date = "2020-06-30"

    with os.scandir(basedir) as entries:
        for f in entries:
            filename = basedir + '/' + f.name
            coinname = f.name.split('.')[0]
            temp = pd.read_csv(filename, parse_dates=True)
            temp[['Name']] = coinname
            if (datetime.datetime.strptime(temp.loc[0,'Datetime'], "%Y-%m-%d %H:%M:%S") <= datetime.datetime.strptime(start_date, "%Y-%m-%d") and \
                    datetime.datetime.strptime(temp.loc[len(temp)-1, 'Datetime'], "%Y-%m-%d %H:%M:%S") > datetime.datetime.strptime(end_date, "%Y-%m-%d")):
                temp = temp[temp['Datetime'] >= start_date]
                temp = temp[temp['Datetime'] <= end_date]
                mdf = pd.concat([mdf, temp])
                listdf.append(temp.copy())
                print(coinname)
                tickerCnt += 1



    linecnt = 0
    position = 0
    longlist = {}

    unitbuy = 10000
    buycash = 0
    port_value = 0

    backwatch_hours = 24*7
    buydelay = 24
    stepcnt = 0

    init_cash = 150000
    final_value = init_cash
    commision = 0.001

    vdf = pd.DataFrame()

    for i in range(0,len(listdf[0])):

        if i > backwatch_hours:
            curdate = listdf[0].iloc[i, 0]
            datetype = datetime.datetime.strptime(curdate, "%Y-%m-%d %H:%M:%S")
            pastdatetype = datetype - datetime.timedelta(hours=backwatch_hours)
            pastdate = datetime.datetime.strftime(pastdatetype, "%Y-%m-%d %H:%M:%S")


            ## get close price in target old/cur datetime
            curClose = mdf[mdf['Datetime'] == curdate][['Close', 'Name']].copy()
            curClose.index = range(0, len(curClose))
            pastClose = mdf[mdf['Datetime'] == pastdate][['Close', 'Name']].copy()
            pastClose.index = range(0, len(pastClose))

            ## merge for diff rate caculation and descending sort by diff rate
            mclose = pd.merge(curClose, pastClose, how='left', on='Name')
            mclose[['Diff']] = (mclose['Close_x']-mclose['Close_y'])/ mclose['Close_y']
            mclose_p = mclose.sort_values(by=['Diff'], axis=0, ascending=False).copy()
            mclose_m = mclose.sort_values(by=['Diff'], axis=0, ascending=True).copy()

            ## make coin list for long position
            if position == 1 and stepcnt == 0:

                ## calc sell results
                buycash = 0
                port_value = 0

                for key, val in longlist.items():

                    buycash += unitbuy
                    cur_price = curClose[curClose['Name'] == key].iloc[0, 0]
                    profit = (cur_price - val) / val
                    result_value = unitbuy + (unitbuy * profit)
                    port_value += result_value

                # for key, val in shortlist.items():
                #
                #     buycash += unitbuy
                #     cur_price = curClose[curClose['Name'] == key].iloc[0, 0]
                #     profit = (val - cur_price) / val
                #     result_value = unitbuy + (unitbuy * profit)
                #     port_value += result_value

                final_value = (final_value - buycash) - (buycash*commision)
                final_value = (final_value + port_value) - (port_value*commision)

                # save result
                vdf = vdf.append(pd.DataFrame({'Buy':buycash, 'Evaluation':port_value, 'Profit':(port_value-buycash)/buycash,
                                               'PortValue':final_value}, index=[curdate]))

                #init position
                position = 0

                #buy
            if (i % 24) == 0:
                longlist = {}
                shortlist = {}
                for j in range(0, 10):
                    longlist[mclose_p.iloc[j]['Name']] = curClose[curClose['Name']==mclose_p.iloc[j]['Name']].iloc[0,0]
                    shortlist[mclose_m.iloc[j]['Name']] = curClose[curClose['Name']==mclose_m.iloc[j]['Name']].iloc[0,0]

                position = 1
                stepcnt = buydelay

            stepcnt -= 1
            stepcnt = max(stepcnt, 0)

    vdf['PortValue'].plot()
    print("Init cash: %.2f, Final Value: %.2f, Profit: %.2f" % (init_cash, final_value, (final_value-init_cash)/init_cash))
