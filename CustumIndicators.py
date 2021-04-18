import datetime
import FinanceDataReader as fdr
import cufflinks as cf
import chart_studio.plotly as py
import pandas as pd
import numpy as np
import backtrader as bt
import math
import talib


class VolumeRatio(bt.Indicator):
    lines = ("vr",)
    params = (("period", 14),)
    iterval = 0

    def next(self):
        self.iterval += 1
        self.data.upvol[0] = (
            self.data.volume[0]
            if self.data.close[0] > self.data.close[-1]
            else self.data.volume[0] / 2
            if self.data.close[0] == self.data.close[-1]
            else 0
        )

        if self.iterval > self.p.period:
            sumupvol = sum(self.data.upvol.get(size=self.p.period))
            sumdownvol = sum(self.data.volume.get(size=self.p.period))
            self.lines.vr[0] = 100 * (sumupvol / sumdownvol)


def practiceCode():
    format = "%Y-%m-%d %H:%M:%S"
    datetime_str = "2018-01-12 11:22:12"
    datetime_dt = datetime.datetime.strptime(datetime_str, format)
    print(type(datetime_dt))

    index = pd.date_range("2019-01-01", "2019-10-01", freq="B")
    ser = pd.Series(range(len(index)), index=index)

    df2 = pd.read_csv("datas/btcusd.csv")
    df2.reset_index()
    df2["Timestamp"] = pd.to_datetime(df2["Timestamp"])
    df2.rename(names={"Timestamp": "Date"})

    df = pd.read_csv("datas/coinbaseUSD.csv", names=["Date", "Price", "Volume"])
    df3 = pd.read_csv(
        "datas/tt.csv",
        usecols=[0, 1, 2, 3, 4, 5],
        names=["Date", "Open", "High", "Low", "Close", "Volume"],
    )
    df5 = pd.read_csv(
        "datas/ttt.csv",
        usecols=[0, 1, 2, 3, 4, 5],
        names=["Date", "Open", "High", "Low", "Close", "Volume"],
    )
    df["Date"] = pd.to_datetime(df["Date"], unit="s")
    df3["Date"] = pd.to_datetime(df3["Date"], unit="s")
    df5["Date"] = pd.to_datetime(df5["Date"], unit="s")

    df = df.set_index(["Date"])
    df3 = df3.set_index(["Date"])
    df5 = df5.set_index(["Date"])

    df = df["2015-03-01":]
    df2 = df[["Price"]].resample("T").first().fillna(method="ffill").copy()
    df2 = df2.rename(columns={"Price": "Open"})
    df2[["High"]] = df[["Price"]].resample("T").max().fillna(method="ffill").copy()
    df2[["Low"]] = df[["Price"]].resample("T").min().fillna(method="ffill").copy()
    df2[["Close"]] = df[["Price"]].resample("T").last().fillna(method="ffill").copy()
    df2[["Volume"]] = df[["Volume"]].resample("T").sum().fillna(0).copy()

    def resampleCandle(df, str):
        tempdf = df[["Open"]].resample(str).first().copy()
        tempdf[["High"]] = df[["High"]].resample(str).max().copy()
        tempdf[["Low"]] = df[["Low"]].resample(str).min().copy()
        tempdf[["Close"]] = df[["Close"]].resample(str).last().copy()
        tempdf[["Volume"]] = df[["Volume"]].resample(str).sum().copy()
        return tempdf

    # merge
    df4 = df2.merge(
        df3,
        on=["Open", "High", "Low", "Close", "Volume"],
        how="outer",
        left_index=True,
        right_index=True,
    )
    df6 = df4.merge(
        df5,
        on=["Open", "High", "Low", "Close", "Volume"],
        how="outer",
        left_index=True,
        right_index=True,
    )

    tr = pd.date_range("2015-03-01", "2021-01-29", freq="T")
    dd = pd.DataFrame(range(len(tr)), index=tr)

    ddd = df6[["Close"]].merge(dd, how="outer", left_index=True, right_index=True)
    ddd[ddd["Close"].isna()]

    dfk = pd.read_csv(
        "datas/bitstampUSD_1min_kaggle.csv",
        index_col="Timestamp",
        parse_dates=True,
        date_parser=lambda x: pd.to_datetime(x, unit="s"),
    )

    df2 = df[["Price"]]

    df2 = df2.fillna(method="ffill")

    df3 = df[["Volume"]]
    df3 = df3.fillna(0)

    df2 = df2.resample("T").last()
    df3 = df[["Price"]].resample("T").first()
    df3["Price"] = df3["Price"].fillna(method="ffill")
    df3["Open"] = df["Price"].fillna(method="ffill").resample("T").first()
    df3 = df3.resample("T").sum()

    df2 = df2.fillna(method="ffill")

    df4 = df2.merge(df3, left_index=True, right_index=True)

    #####
    df = pd.read_csv("datas/btc_1min.csv", index_col="Date")
    cf.go_offline(connected=True)
    df.iplot()

    cf.go_offline(connected=True)

    df = fdr.DataReader("AAPL", "2018")
    df["Close"].iplot()

    cf.go_offline(connected=True)
    df = fdr.DataReader("AAPL", "2018")
    df[["Close"]].plot()

    talib.MA(df["Close"])
    import quandl

    quandl.ApiConfig.api_key = "EW2NhKzjjUksbmKJCY6z"

    import pandas_datareader.data as web

    symbol = "ZFB/AAPL"
    df = web.DataReader(symbol, "quandl", "2019-01-01", api_key="EW2NhKzjjUksbmKJCY6z")

    return 1

