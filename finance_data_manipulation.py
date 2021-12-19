import chart_studio.plotly as py
import FinanceDataReader as fdr
import pandas as pd
import cufflinks as cf
import numpy as np


datas = np.arange(0, 10, 0.5)
datas = datas.reshape(-1, 4)

df = pd.DataFrame(data=datas, columns=['a', 'b', 'c', 'd'])
df.index = range(4, 4+ len(df))

def loadCSV(filename):
    df = pd.read_csv(filename, index_col=None)
    # sorting by fiscal date
    df[['ReportName', 'Year', 'Month', 'dummy']] = df['report_nm'].str.split(pat=r'[(.)]', expand=True)
    df['date'] = df['Year'] +'-'+ df['Month']
    df.sort_values(by=['corp_name','Year','Month'], inplace = True)
    df.index = range(len(df))
    df.loc[:,'Sales':'NetIncome'] = df.loc[:,'Sales':'NetIncome'].astype(float)
    return df


file1 = 'datas/finance2/fdata_by_count_all_working_csv.csv'
file2 = 'datas/finance2/fdata_by_count_all_2nd.csv'

# df1 = loadCSV(file1)
# df2 = loadCSV(file2)

# df_m = df1.merge(df22, how='left', on='rcept_no')
# for i in range(len(df_m)):
#     if df_m.loc[i, 'NetIncome'] == -1:
#         df_m.loc[i, 'NetIncome'] = df_m.loc[i, 'NetIncome2']

# after merge and with empty date
# df[['Sales_diff','GrossProfit_diff', 'OperIncome_diff','NetIncome_diff']] = df.loc[:,'Sales':'NetIncome'].diff()
# df['shiftedName'] = df['ReportName'].shift()

date_base = pd.DataFrame(pd.date_range(start = '2000-03', end='2021-06', freq='3M'))
date_base.columns = ['date_full']
date_base['date'] = date_base['date_full'].dt.strftime('%Y-%m')
date_base = date_base.set_index('date')


company_names = list(df['corp_name'].unique())
mdf = pd.DataFrame()
for name in company_names:
    tempdf = df[df['corp_name']==name].copy()
    tempdf.index = range(len(tempdf))

    #find first quater's report
    # rname_idx = tempdf.columns.get_loc('ReportName')
    # start_idx = -1
    # for i in range(len(tempdf)):
    #     if "분기" in tempdf.iloc[i,rname_idx].replace(" ", "") and len(tempdf) > i + 1 and "반기" in tempdf.iloc[i+1,rname_idx].replace(" ", ""):
    #         start_idx = i
    #         break
    #
    # if start_idx == -1:
    #     start_idx = 0


    start_idx = 0
    tempdf = tempdf.iloc[start_idx:].copy()
    tempdf.index = range(len(tempdf))


    start = tempdf['date'].iloc[0]
    end = tempdf['date'].iloc[-1]
    date_temp = date_base[start:end].copy()
    tdf = tempdf.merge(date_temp, on='date', how='outer').copy()
    tdf.sort_values(by=['date'], inplace = True)
    tdf[['corp_code', 'corp_name', 'stock_code', 'corp_cls', 'flr_nm']] = tdf[
        ['corp_code', 'corp_name', 'stock_code', 'corp_cls', 'flr_nm']].fillna(method='ffill')
    tdf[['Sales', 'GrossProfit', 'OperIncome', 'NetIncome', 'CurrencyUnit']] = tdf[
        ['Sales', 'GrossProfit', 'OperIncome', 'NetIncome', 'CurrencyUnit']].fillna(-1)
    tdf.fillna("", inplace=True)
    tdf['Year'] = tdf['date'].str[:4]
    tdf['Month'] = tdf['date'].str[5:7]
    tdf.loc[:, 'Sales':'NetIncome'] = tdf.loc[:, 'Sales':'NetIncome'].apply(lambda x: x * tdf['CurrencyUnit'])
    tdf['CurrencyUnit'] = 1.0
    mdf = pd.concat([mdf, tdf])
    mdf.index = range(len(mdf))


print("End")

# fill na report


# tempdf.loc[:,'Sales':'NetIncome'] = tempdf.loc[:,'Sales':'NetIncome'] * tempdf['CurrencyUnit']