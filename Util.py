import plotly as pp
import pandas as pd
def plot2(df):
    dfi = df.to_iplot()
    pp.offline.plot(dfi)