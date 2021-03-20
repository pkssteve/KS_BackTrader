import chart_studio.plotly as py
import FinanceDataReader as fdr
import pandas as pd
import cufflinks as cf
cf.go_offline(connected=True)

df = fdr.DataReader('AAPL', '2018')
df['Close'].iplot()
