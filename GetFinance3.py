import FinanceDataReader as fdr

fdf = fdr.StockListing('ETF/US')


start_date = '2010-01-01'
end_date = '2021-12-15'
symbol_list = fdf['Symbol'].to_list()
# symbol_list.extend(['US500', 'IXIC', 'DJI'])
i = 0
for sym in symbol_list:
    try:
        i= i+1
        print(i,'th symbol : ', sym)
        df = fdr.DataReader(sym, start_date, end_date)
        df.to_csv(f'./datas/STOCK/{sym}.csv')
        df.to_csv(f'./datas/ETF/{sym}.csv')
    except Exception as ex:
        pass


pass