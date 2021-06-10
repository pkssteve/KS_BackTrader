import FinanceDataReader as fdr


df_krx = fdr.StockListing('KRX')

df_kosdaq = df_krx[df_krx['Market']=='KOSDAQ']

df_kosdaq = df_kosdaq[df_kosdaq['ListingDate']>='2010-01-01']