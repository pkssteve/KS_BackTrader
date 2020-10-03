'''
The purpose of this script is to fetch free intraday market data
from Google Finance and load it into a Pandas DataFame.
Designed for Python 3.6
'''

import pandas as pd
import numpy as np
import urllib.request
import datetime as dt
import sys
import time


class Intraday_Google_Finance(object):

    def get_intraday_google_data(symbol, interval, lookback):
        url_root = 'http://www.google.com/finance/getprices?i='
        url_root += str(interval) + '&p=' + str(lookback)
        url_root += 'd&f=d,o,h,l,c,v&df=cpct&q=' + symbol
        # print("Requesting URL = " + url_root)
        with urllib.request.urlopen(url_root) as response:
            data = response.read().splitlines()
            # actual data starts at index = 7
        parsed_data = []
        anchor_stamp = ''
        end = len(data)
        for i in range(7, end):
            cdata = data[i].split(str(',').encode())
            if str('a').encode() in cdata[0]:  # new trading day
                anchor_stamp = cdata[0].replace(str('a').encode(), str('').encode())
                cts = int(anchor_stamp)
            else:  # extension of current trading day
                try:
                    coffset = int(cdata[0])
                    cts = int(anchor_stamp) + (coffset * int(interval))
                    parsed_data.append((dt.datetime.fromtimestamp(float(cts)).strftime("%Y-%m-%d"),
                                        dt.datetime.fromtimestamp(float(cts)).strftime("%H:%M"),
                                        float(cdata[1]),
                                        float(cdata[2]),
                                        float(cdata[3]),
                                        float(cdata[4]),
                                        float(cdata[5])))
                except:
                    print("Unexpected error:", sys.exc_info()[0])
                    pass  # for time zone offsets thrown into data
        df = pd.DataFrame(parsed_data, columns=['date', 'time', 'o', 'h', 'l', 'c', 'v'])
        return df  # returns a panda dataframe

    def write_intraday_google_data(dataFrame, symbol):
        print("Writing data: " + symbol)
        filePath = 'C:\\Users\All Users\Desktop\Market Data\\'  # filepath - requires adjustment
        filePath += symbol + '_' + dataFrame['date'][dataFrame.index[-1]] + ".csv"
        dataFrame.to_csv(path_or_buf=filePath)

    if __name__ == '__main__':
        print("Starting to load DataFrame...")
        basket = ["SPY", "MMM", "IBM"]  # List of securities to download
        for sec in basket:
            security = get_intraday_google_data(sec, 60, 5)  # ymbol, interval, rolling lookback
            write_intraday_google_data(security, sec)
            time.sleep(2)  # pause 2 seconds in between requests

        print("Done.")