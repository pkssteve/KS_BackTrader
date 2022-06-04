import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
import datetime

plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'AppleGothic'

us_dir = './datas/STOCK/'
ko_dir = './datas/KOSPI_D_2/'

us_files =[us_dir+f for f in os.listdir(us_dir)]
ko_files = [ko_dir+f for f in os.listdir(ko_dir)]

us_df = pd.DataFrame(columns=['Date'])
for us_f in us_files:
    df = pd.read_csv(us_f)
    name = os.path.splitext(os.path.basename(us_f))[0]
    if 'DS_Store' in name:
        continue
    df['pct_change'] = df['Close'].pct_change()
    # df['pct_change'] = df['pct_change'] * 100
    # df['pct_change'] = df['pct_change'].map(lambda x : x * 100 +100)
    # df['pct_change'] = df['pct_change'].map(lambda x : 1 if x >= 0 else -1)
    # df[df['pct_change'] < 0]['pct_change'] = -1
    df = df.rename(columns={'pct_change': name})
    df = df.iloc[1:].copy()
    us_df = us_df.merge(df[['Date', name]], on='Date',  how='outer')

ret_df = pd.DataFrame(columns=['Start','End', 'Pair_A', 'Pair_B', 'Corr'])

ratelist = []
# columns=['Base', 'Monitor', 'HitRatio', 'StartCash', 'ResultCash', 'Alpha', 'StartDate', 'EndDate', 'TotalDays', 'HitDays']
btest_df = pd.DataFrame()
for ko_f in ko_files:
    df = pd.read_csv(ko_f)
    df['pct_change'] = df['Close'].pct_change()
    # df['pct_change'] = df['pct_change'] * 100
    # df['pct_change'] = df['pct_change'].map(lambda x: x * 100 + 100)
    # df['pct_change'] = df['pct_change'].map(lambda x: 1 if x >= 0 else -1)
    # df[df['pct_change'] >= 0] = 1
    # df[df['pct_change'] < 0] = -1
    name = os.path.splitext(os.path.basename(ko_f))[0]
    name = name.split('_')[1]
    if 'DS_Store' in name:
        continue
    df = df.rename(columns={'pct_change': name, 'Datetime':'Date'})
    df = df.dropna(how='any')
    if df[name].min() > 1000:
        df[name] = df[name].map(lambda x:x/100)
    ko_df = df[['Date', name]]

    ko_df = ko_df.merge(us_df, on='Date', how='inner')
    # ko_df[name] = ko_df[name].shift(-7)
    # ko_df = ko_df.iloc[:-7]
    ko_df = ko_df.dropna(axis=1, how='any').reset_index(drop=True)
    cols = list(ko_df.columns)
    cols.remove(name)
    cols.remove('Date')
    ko_df = ko_df.iloc[:].copy().reset_index(drop=True)
    # sorted_ko_df = ko_df.sort_values(by=name).reset_index(drop=True)


    for col in cols:
        monitor_length = len(ko_df) // 2 # get the length at 33% of total length
        # monitor_length = len(ko_df) - (len(ko_df) // 3)
        ko_df_temp = ko_df.iloc[:monitor_length].copy().reset_index(drop=True)
        ko_df_test = ko_df.iloc[monitor_length:].copy().reset_index(drop=True)
        ko_df_plus = ko_df_temp[ko_df_temp[col] >= 0].copy()
        ko_df_plus = ko_df_plus.reset_index(drop=True)
        ko_df_plus[col] = (ko_df_plus[col] > 0) & (ko_df_plus[name] > 0)
        if ko_df_plus[col].sum() == 0:
            continue
        rate = ko_df_plus[col].sum() / len(ko_df_plus[col])
        if rate > 0.58 and len(ko_df_plus[col]) > 100:
            ratelist.append(rate)
            # print(len(ko_df2[col]),rate)
            base_cash = 10000
            max = base_cash
            mdd = 0
            for i in range(len(ko_df_test)):
                if ko_df_test[col][i] > 0:
                    base_cash += base_cash * ko_df_test[name][i]
                    max = max if max >= base_cash else base_cash
                    mdd = mdd if mdd < ((base_cash-max)/max)*100 else ((base_cash-max)/max)*100
            # print('Base case result :', base_cash)
            s = datetime.datetime.strptime(ko_df['Date'].min(), '%Y-%m-%d')
            e = datetime.datetime.strptime(ko_df['Date'].max(), '%Y-%m-%d')
            d = e-s
            mons = d.days // 30
            cagr = ((base_cash / 10000) ** (1 / mons) - 1) * 100
            datas = [name, col, rate, 10000, base_cash, ((base_cash-10000)/10000) * 100, cagr, mdd, ko_df_test.Date.min(), ko_df_test.Date.max(), len(ko_df_test), len(ko_df_plus[col]), mons]
            print(name, col, rate, base_cash, ko_df_test.Date.min(), ko_df_test.Date.max(), len(ko_df_test), len(ko_df_plus[col]))
            btest_df = btest_df.append(pd.DataFrame(np.array(datas).reshape(1, -1)))
            continue


    # print('length of ratelist', len(ratelist))


    corr_df = ko_df.corrwith(ko_df[name])
    high_corr = corr_df[(corr_df > 0.6) & (corr_df < 0.989)]
    for i in range(len(high_corr)):
        ret_df = ret_df.append({'Start':ko_df.Date.min(),'End':ko_df.Date.max(),'Pair_A':name, 'Pair_B':high_corr.index[i],  'Corr':high_corr.iloc[i]}, ignore_index=True)
        if high_corr.iloc[i] > 0.9:
            print(ko_df.Date.min(), ko_df.Date.max(), name, high_corr.index[i], high_corr.iloc[i])
            a = 0
btest_df.columns = ['Base', 'Monitor', 'HitRatio', 'StartCash', 'ResultCash', 'Alpha', 'CAGR', 'MDD', 'StartDate', 'EndDate', 'TotalDays', 'HitDays', 'Months']
btest_df[['Alpha', 'CAGR', 'MDD', 'TotalDays', 'Months']] = btest_df[['Alpha', 'CAGR', 'MDD', 'TotalDays', 'Months']].astype(float)
btest_df = btest_df.reset_index(drop=True)
print('Finished')

