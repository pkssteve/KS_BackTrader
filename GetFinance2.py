import dart_fss as fss
import time
import FinanceDataReader as fdr
# import dart_fss_classifier
# assert dart_fss_classifier.attached_plugin() == True
import OpenDartReader as odr

rept_code_list = ['11013', '11012', '11014', '11011']  # 1분기, 반기, 3분기, 사업보고서 순

api_key = '030931185c55a687211970bb072de0382b4a0ffd'
dart = odr(api_key)
fss.set_api_key(api_key)

fdf = fdr.StockListing('KRX')
# df_spx = fdr.StockListing('S&P500')
fdf = fdf[fdf['Market']!='KONEX'].copy()
fdf.index = range(len(fdf))

fdf['Name'] = fdf['Name'].str.replace(' ','')
names = fdf['Name'].to_list()

corp_list = fss.get_corp_list()
sam = corp_list.find_by_corp_name('삼성전자', exactly=True)[0]
co_list = list(corp_list.corps)

co_list.sort(key= lambda x : x.to_dict()['corp_code'])
ret = dart.finstate('삼성전자', 2018)
# ret3 = dart.finstate_all('삼성전자', 2018, reprt_code='11013')
count = 0
last_save_count = 0

for fs in co_list:
    if fs.to_dict()['corp_name'] not in names:
        continue
    try:
        count += 1
        if count < 2684:
            continue
        data = fs.extract_fs(bgn_de='20200101', end_de='20210101', report_tp='quarter')
        data.save()

    except Exception as ex:
        time.sleep(0.7)
    finally:
        print('Current Count :', count)



