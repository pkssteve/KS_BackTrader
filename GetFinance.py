import pandas as pd
import OpenDartReader
import sqlite3
import FinanceDataReader as fdr
import dart_fss as fss
import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString
import re
import cssutils
import time
css_parser = cssutils.CSSParser()

tablenum1 = [7,14]
tablenum2 = [6,11]

def findCurrencyUnit(ntags):
    res = ''
    existUnit = False
    for t in ntags:
        if type(t) != NavigableString:
            if "단위" in t.text:
                cur_text = t.text
                existUnit = True
                toks = cur_text.split(":")
                if len(toks) > 0:
                    selected_text = toks[len(toks)-1]
                    selected_text = selected_text.replace(' ', '')
                    selected_text = selected_text.replace('\xa0', '')
                    selected_text = selected_text.replace('\n', '')
                    selected_text = selected_text.replace('\\u', '')
                    selected_text = selected_text.replace(')', '')
                    res = selected_text
                    break

    return res, existUnit

def printError(sentence):
    print('\033[91m%s' % sentence)
    global gdf_ErrorReport
    global gCurDF
    gCurDF[['err_str']] = sentence
    gdf_ErrorReport = gdf_ErrorReport.append(gCurDF.copy())

def getColSpan(_head_rows): # get colspan of first column if column rows are 2

    cols = 1
    i = 0
    for row in _head_rows:
        i += 1
        for field in row.contents:
            if type(field) == NavigableString:
                continue
            tags = re.findall(r'\d+', field.text)
            if len(tags) == 0:
                continue
            # txt = field.text
            # txt = txt.replace(" ", "")
            # txt = txt.replace("\n", "")
            # txt = txt.replace("\xa0", "")
            # txt = txt.replace("\\u", "")
            # if "개월" in txt:
            if 'colspan' in field.attrs:
                cols = int(field['colspan'])
            else:
                cols = 1
            break

    return cols



def getFinanceValues(soup, typenum, tags_col2, tags2, dic, tags2_second, tags_third = None):
    df = pd.DataFrame()

    head_rows = soup.select("body > table:nth-child(%d) > thead > tr" % (tableIndex))
    headers = getTableHeaders(head_rows)

    print('Table Headers')
    for li in headers:
        print(li)

    k = 0
    colspan = 1
    if len(head_rows) == 0:
        while "colspan" in tags2[k].attrs:
            colspan = int(tags2[k].attrs['colspan'])
            k += 1
    else:
        colspan = getColSpan(head_rows)
    print('col span %d' % colspan)

    if len(headers) > 0:
        row = headers[0]
        if len(row) < 2 and len(headers) > 1:
            row = headers[1]
        if len(row) > 1:
            row_with_digit = re.findall(r'\d+', row[1])
            if len(row_with_digit) > 0:
                first = int(row_with_digit[0])
            else:
                printError('There is no digit in a row============================================')
                return df
            if len(row) > 2:
                second = re.findall(r'\d+', row[2])
                if len(second) > 0:
                    second = int(second[0])
                else:
                    second = 0
                if first < second:
                    printError("===========================================  the quarter order was reversed !! first %d second %d" % (first, second))
        else:
            printError("It couldn't check quarter ordering")
    else:
        printError("===============================================  there is no header !!")
        if len(tags_col2) > 1:
            if '개월' in tags_col2[1].text.replace(" ", ""):
                if type(tags_col2[1]) != NavigableString:
                    if 'colspan' in tags_col2[1].attrs:
                        colspan = int(tags_col2[1].attrs['colspan'])




    toks_col2 = str(tags_col2).split('<br/>')
    if len(toks_col2) < 38:
        toks_col2 = str(tags_col2).split('</td>')
    toks2 = str(tags2).split('<br/>')
    if len(toks2) < 38:
        toks2 = str(tags2).split('</td>')
    toks2_second = str(tags2_second).split('<br/>')
    if len(toks2_second) < 38:
        toks2_second = str(tags2_second).split('</td>')


    sales = getValues(tags_col2, tags2, dic["매출"])
    if sales == -1 and colspan == 2:
        sales = getValues(tags_col2, tags2_second, dic["매출"])

    costs = getValues(tags_col2, tags2, dic["매출원가"])
    if costs == -1 and colspan == 2:
            costs = getValues(tags_col2, tags2_second, dic["매출원가"])
    costs = costs if costs > 0 else -costs

    if typenum == 1:
        grossProfit = getValues(tags_col2, tags2, dic["매출총이익"])  # 매출총손실
    else:
        grossProfit = sales - costs

    if grossProfit == -1:
        grossProfit = getValues(tags_col2, tags2, dic["매출총이익2"])
        if grossProfit == -1 and colspan == 2:
            grossProfit = getValues(tags_col2, tags2_second, dic["매출총이익"])



    costs2 = getValues(tags_col2, tags2, dic["판매비"], -1, colspan)
    if costs2 == -1 and colspan == 2:
        costs2 = getValues(tags_col2, tags2_second, dic["판매비"], -1, colspan)
    if costs2 == -1:
        costs2 = getValues(tags_col2, tags2, '영업관리비용', -1, colspan)
        if costs2 == -1:
            costs2 = getValues(tags_col2, tags2, '판매관리비', -1, colspan)
            if costs2 == -1:
                costs2 = 0

    operIncome = getValues(tags_col2, tags2, dic["영업이익"])  # 영업손실
    if operIncome == -1:
        operIncome = getValues(tags_col2, tags2, dic["영업이익2"])
        if operIncome == -1 and colspan == 2:
            operIncome = getValues(tags_col2, tags2_second, dic["영업이익"])
        if operIncome == -1:
            operIncome = getValues(tags_col2, tags2, '영업손익')

        # if operIncome > 0:
        #     operIncome = -operIncome
    netIncome = getValues(tags_col2, tags2, dic["당기순이익"])
    if netIncome == -1:
        netIncome = getValues(tags_col2, tags2, dic["당기순이익2"])
        if netIncome == -1 and colspan == 2:
            netIncome = getValues(tags_col2, tags2_second, dic["당기순이익"])

    if sales != -1 and costs != -1 and costs!= 0 and abs(sales - (costs + grossProfit)) <= 2:
        print('Sales of %s was properly parsed' % code)
    else:
        printError('Wrong!! Sales of %s was wrong. sales %d cost %d gross profit %d diff %d' % (
        code, sales, costs, grossProfit, sales - (costs + grossProfit)))

    if grossProfit != - 1 and grossProfit != 0 and costs2 != -1 and abs(grossProfit - (costs2 + operIncome)) <= 2:
        print('Gross Profit values of %s was properly parsed' % code)
    else:
        costs3 = 0
        if grossProfit == operIncome:
            grossProfit += costs2
        else:
            costs3 = getValues(tags_col2, tags2, '대손상각비', -1, colspan)
        if grossProfit != - 1 and costs2 != -1 and abs(grossProfit - (costs2 + costs3 + operIncome)) <= 2:
            print('Gross Profit values of %s was properly parsed' % code)
        else:
            printError('Wrong!! Gross Profit of %s was wrong. gross profit %d cost2 %d operating income %d diff %d ' % (
            code, grossProfit, costs2, operIncome, grossProfit - (costs2 + operIncome)))

    df = pd.DataFrame([[sales, grossProfit, operIncome, netIncome]])
    df.columns = ['Sales', 'GrossProfit', 'OperIncome', 'NetIncome']

    return df

def getTableHeaders(_head_rows):
    headers = []
    for i in range(len(_head_rows)):
        li = _head_rows[i].text.split("\n")
        for j in range(len(li)):
            li[j] = li[j].replace(' ', "")
            li[j] = li[j].replace('\\u', "")
            li[j] = li[j].replace("\xa0", "")
        for j in range(li.count('')):
            li.remove('')

        headers.append(li)
    return headers


def findWordIndex(lines, findWord):

    i = 0
    for sentence_raw in lines:
        if type(sentence_raw) != str:
            sentence = sentence_raw.text
        else:
            sentence = sentence_raw
        sentence = sentence.replace("\xa0", "")
        if findWord in sentence.replace(" ", ""):
            return i
        i += 1

    return -1

def getValues(colnames, values, word, idx = -1, colspan = 1, dt = 1):
    amount = -1
    datatype = dt
    if len(colnames) <3:
        toks_col2 = str(colnames).split('<br/>')
        if len(toks_col2) < 34:
            toks_col2 = str(toks_col2).split('</td>')
        colnames = toks_col2

    values_back = values

    if idx == -1:
        index = findWordIndex(colnames, word)
    else:
        index = idx
    if index == -1:
        return -1


    if len(values) < 3:
        datatype = 2
        values_bak = values
        toks= str(values).split('<br/>')
        if len(toks) < 34:
            toks = str(toks).split('</td>')
        values = toks

    if len(values)-1 < index:
        return amount

    if datatype == 1:
        if len(values[index].contents) > 1:
            foundstr = ''
            for cont in values[index].contents:
                if cont != '\n':
                    if type(cont) == NavigableString:
                        foundstr = cont
                        break
                    else:
                        foundstr = cont.text
                        break

            # if foundstr == '':
            #     foundstr = values[index].contents[0]
        else:
            foundstr = values[index].text
    else:
        foundstr = values[index]

    if '">' in foundstr:
        foundstr = foundstr[foundstr.find('">')+1:]
    tags = re.findall(r'△*Δ*\(*-*\)*[\d+,*]+\)*', foundstr)
    if len(tags) == 0:
        if '판매비' in word and colspan == 1:
            c1 = getValues(colnames, values_back, "판매비", index + 1, colspan)
            c2 = getValues(colnames, values_back, "관리비", index + 2, colspan)
            amount = c1 + c2
            amount = amount if amount > 0 else -amount
        return amount

    if datatype == 2:
        foundstr = tags[len(tags)-1]

    dd = foundstr.split('\n')

    foundstr = foundstr.replace('\n', "")
    foundstr = foundstr.replace('(-)', '-')
    foundstr = foundstr.replace('--', '-')
    foundstr = foundstr.replace('△', '-')
    foundstr = foundstr.replace('Δ', '-')
    foundstr = foundstr.replace('\xa0', '')
    if '(' in foundstr:
        foundstr = foundstr.strip('()')
        foundstr = foundstr.replace(",", "")
        if not foundstr.isnumeric():
            printError("There is no pure numeric==========================================")
            return -1

        amount = -int(foundstr.replace(",", ""))
        if type(colnames[index]) == str:
            checkstr = colnames[index]
        else:
            checkstr = colnames[index].text
        if '손실(이익)' in checkstr.replace(" ", ""):
            amount = amount if amount > 0 else -amount
    else:
        foundstr_temp = foundstr.replace(",", "")
        foundstr = foundstr_temp.replace(" ", "")
        if foundstr.replace('-', '').isnumeric():
            amount = int(foundstr.replace(",", ""))
        else:
            printError('It is not numeric  ====================================================')
        if '손실' in word:
            amount = -amount if amount > 0 else amount

    return amount

def findTableIndex(word, startIndex = 0):
    for i in range(startIndex, 30):
        tags = soup.select("body > table:nth-child(%d) > tbody > tr > td:nth-child(1)" % i)
        if len(tags)>0:
            toks_col = str(tags).split('<br/>')
            for sentence in toks_col:
                sentence = sentence.replace("\xa0", "")
                if word in sentence.replace(" ", ""):
                    return i
    return -1


api_key = '030931185c55a687211970bb072de0382b4a0ffd'
# fss.set_api_key(api_key)
dart = OpenDartReader(api_key)
#
# corp_list = fss.get_corp_list()
# sam = corp_list.find_by_corp_name('삼성전자')[4]
# data = sam.extract_fs(bgn_de = '20050101', end_de = '20100101')


con = sqlite3.connect('finance.db')

quartcode = ['11013', '11012', '11014', '11011'] # [1분기, 반기, 3분기, 사업]보고서
monthToQuarter ={3:4, 6:1, 9:2, 12:3}
quarterToWords ={1:"분기", 2:"반기", 3:"분기", 4:"사업"}
strToQuater = {"분기보고서3":1, "반기보고서6":2, "분기보고서9":3, "사업보고서12":4,
               "사업보고서3":4, "분기보고서6":1, "반기보고서9":2, "분기보고서12":3}

fdic = {"매출":"매출", "매출원가":"매출원가", "매출총이익":"매출총이익", "매출총이익2":"매출총손실", "판매비":"판매비", \
                "영업이익":"영업이익", "영업이익2":"영업손실", "당기순이익":"당기순이익", "당기순이익2":"당기순손실"}
fdic2 = {"매출":"영업수익", "매출원가":"영업비용", "매출총이익":"매출총이익", "매출총이익2":"매출총손실", "판매비":"판매비", \
        "영업이익":"영업이익", "영업이익2":"영업손실", "당기순이익":"당기순이익", "당기순이익2":"당기순손실"}
unit_dic = {"원":1,"십원":10, "백원":100, "천원":1000, "만원":10000, "십만원":100000, "백만원":1000000, "천만원":10000000,
            "억원":100000000, "억":100000000, "십억원":1000000000, "십억":1000000000, "백억":10000000000, "백억원":10000000000, "천억원":100000000000, "천억":100000000000}
        #매출총이익=매출-매출원가 계산값 사용해야함
        #검증식은 매출총이익-판관비 하면 영업이익이 나와야함
# data를 종목별로 다 가져와서 df에 넣은 후 to_sql()을 사용한다.

#전체 상장회사 코드리스트를 가져온다.
fdf = fdr.StockListing('KRX')
# df_spx = fdr.StockListing('S&P500')
fdf = fdf[fdf['Market']!='KONEX'].copy()
fdf.index = range(len(fdf))

count = 0
codes = fdf['Symbol'].to_list()


total_df = pd.DataFrame()
start = 0
gCurDF = pd.DataFrame()
gdf_ErrorReport = pd.DataFrame()
# codes= ['010820', '028670', '054300', '225590', '170790', '037030', '037070', '005690', '208340', '046210', '081150', '104480', '246710', '057680', '322180']
for code in codes:
    # if code == '060310':
    #     continue
    isnan = fdf[fdf['Symbol'] == code]['Sector'].isna().iloc[0]
    if len(code) != 6 or isnan == True:
        continue

    df = pd.DataFrame()

    # if code != '265520' and start == 0:
    #     continue
    # else:
    start = 1

    count += 1

    print('\n\nthe %d th code' % count)

    if "스팩" in fdf[fdf['Symbol'] == code]['Name'].iloc[0]:
        continue
    # if count < 1950:
    initial_count = 1308
    if count < initial_count:
        continue

    try:
        print('try code %s' % code)
        df = dart.list(code, start='2000-01-01', end='2021-06-30', kind='A')
    except Exception as e:
        stockname = fdf[fdf['Symbol']==code]['Name'].iloc[0]
        print("Code %s error" % code)
        print(e)
        continue

    if start == 0:
        continue

    if len(df) == 0:
        printError("There is no doc list =====================================================")
        continue
    df = df.sort_values(by=['rcept_no'], axis=0, ascending=True)
    df.index = range(len(df))


    # for total list of documents for a company
    for i in range(len(df)):
        time.sleep(0.7)
        rcept_no = df.iloc[i]['rcept_no']
        rcept_dt = df.iloc[i]['rcept_dt']
        report_nm = df.iloc[i]['report_nm']
        if "보고서" not in report_nm:
            continue
        report_str = re.findall('\w\w보고서',report_nm.replace(" ", ""))[0]

        df_cur = pd.DataFrame([df.iloc[i].copy()])
        gCurDF = df_cur.copy()
        gCurDF[['url']] = ''

        report_date_tag = re.findall(r'(\d+.\d+)', report_nm)
        if len(report_date_tag) ==0 :
            printError('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!There is no date')
            continue
        date = re.findall(r'(\d+.\d+)',report_nm)[0]
        report_year = int(date[:4])
        report_month = int(date[5:])
        if '%s%s' % (report_str, report_month) in strToQuater:
            report_quarter = strToQuater['%s%s' % (report_str, report_month)]
        else:
            printError('============================ Invalid Quarter ===================================')

        typenum = 1
        dic = fdic
        parse_type = 1
        try:
            doclist = dart.sub_docs(rcept_no)
        except Exception as e:
            print(e)
        ldoc = doclist[doclist['title'].str.contains(r'\.재무제표$')]
        if len(ldoc) == 0:
            continue
        url  =ldoc.iloc[0][1]

        gCurDF[['url']] = url
        print(report_nm, rcept_no, url)


        try:
            html = requests.get(url).text
        except Exception as ex:
            print(ex)
            time.sleep(60*10)
            html = requests.get(url).text

        # html = html.replace(' ', '')
        soup = BeautifulSoup(html, "html5lib")
        # tags = soup.select("#_per")

        # financial state
        tableIndex = findTableIndex("매출채권")
        tableIndex2 = findTableIndex("영업이익",tableIndex)
        if tableIndex == -1:
            print("there is no table to proper (find:매출채권)")


        tags_col = soup.select("body > table:nth-child(%d) > tbody > tr > td:nth-child(1)" % tableIndex)
        tags = soup.select("body > table:nth-child(%d) > tbody > tr > td:nth-child(2)" % tableIndex)



        toks_col = str(tags_col).split('<br/>')
        toks = str(tags).split('<br/>')

        # Income statement
        tableIndex = findTableIndex("매출총이익")
        if tableIndex == -1:
            tableIndex = findTableIndex("매출총손실")
            if tableIndex == -1:
                print("there is no table to proper (find:매출총이익). changed type2")
                typenum = 2
                dic = fdic2
                tableIndex = findTableIndex("영업수익")
        if tableIndex == -1:
            print("there is no table to find. So skipped this report")
            continue

        currency_unit = 1
        for j in range(1,4):
            tags_tableHeader = soup.select("body > table:nth-child(%d) > tbody > tr > td" % (tableIndex - j))
            currency_unit_str, existUnit = findCurrencyUnit(tags_tableHeader)
            if currency_unit_str != '' and currency_unit_str in unit_dic:
                if j==3:
                    printError('===============================================Warning : unit table index -3')
                break

        if currency_unit_str != '' and currency_unit_str in unit_dic:
            currency_unit = unit_dic[currency_unit_str]
            print("Current Unit : %d" % currency_unit)
        elif existUnit == False:
            printError(f'===========================================there is no current unit in the table. currency_unit_str: {currency_unit_str}')

        tags_col2 = soup.select("body > table:nth-child(%d) > tbody > tr > td:nth-child(1)" % (tableIndex))
        tags2 = soup.select("body > table:nth-child(%d) > tbody > tr > td:nth-child(2)" % (tableIndex))
        tags2_second = soup.select("body > table:nth-child(%d) > tbody > tr > td:nth-child(3)" % (tableIndex))
        tags_op = None
        if tableIndex != tableIndex2:
            tags_op = soup.select("body > table:nth-child(%d) > tbody > tr > td:nth-child(2)" % tableIndex2)


        if (len(tags_col2) == 0) or (len(tags2) == 0):
            print("column lines %d value lines %d. so try parsing using pandas's read_html")
            dfs = pd.read_html(url, header=1)
            parse_type = 2

        df_finance = pd.DataFrame()
        if parse_type == 1:
            df_finance = getFinanceValues(soup, typenum, tags_col2, tags2, dic, tags2_second, tags_op)
        elif parse_type == 2:
            print("Preparing...")



        if len(df_finance) == 0:
            continue

        df_cur[['Sales', 'GrossProfit', 'OperIncome', 'NetIncome']] = [df_finance.iloc[0].copy()]
        df_cur[['URL']] = url
        df_cur[['CurrencyUnit']] = currency_unit

        total_df = total_df.append(df_cur.copy())
        total_df.index = range(len(total_df))

        if count ==30000:
            total_df = total_df[total_df['stock_code']!= code].copy()
            total_df.to_csv(f'datas/finance/fdata_by_count_{initial_count}_{count-1}.csv', index=0)
            gdf_ErrorReport = gdf_ErrorReport[gdf_ErrorReport['stock_code']!=code].copy()
            gdf_ErrorReport.to_csv(f'datas/finance/fdata_error_by_count_{initial_count}_{count-1}.csv', index=0)
        pass

        # 제무제표 가져온다
        # 손익계산서 가져온다
        # data를 df에 넣는다.
    # if count >= 2000:
    #     print("break!!!")
    #     break
    pass

# ==== 0. 객체 생성 ====
# 객체 생성 (API KEY 지정)

print("End !!!!!!!!!!!!!!!!!!!")
exit()
# == 1. 공시정보 검색 ==
# 삼성전자 2019-07-01 하루 동안 공시 목록 (날짜에 다양한 포맷이 가능합니다)
dart.list('005930', end='2019-7-1')

# 삼성전자 상장이후 모든 공시 목록 (5,142 건+)
dart.list('005930', start='1900')

# 삼성전자 2010-01-01 ~ 2019-12-31 모든 공시 목록 (2,676 건)
dart.list('005930', start='2010-01-01', end='2019-12-31')

# 삼성전자 1999-01-01 이후 모든 정기보고서
dart.list('005930', start='1999-01-01', kind='A', final=False)

# 삼성전자 1999년~2019년 모든 정기보고서(최종보고서)
dart.list('005930', start='1999-01-01', end='2019-12-31', kind='A')


# 2020-07-01 하루동안 모든 공시목록
dart.list(end='20200701')

# 2020-01-01 ~ 2020-01-10 모든 회사의 모든 공시목록 (4,209 건)
dart.list(start='2020-01-01', end='2020-01-10')

# 2020-01-01 ~ 2020-01-10 모든 회사의 모든 공시목록 (정정된 공시포함) (4,876 건)
dart.list(start='2020-01-01', end='2020-01-10', final=False)

# 2020-07-01 부터 현재까지 모든 회사의 정기보고서
dart.list(start='2020-07-01', kind='A')

# 2019-01-01 ~ 2019-03-31 모든 회사의 정기보고서 (961건)
dart.list(start='20100101', end='20190331', kind='A')

# 기업의 개황정보
dart.company('005930')

# 회사명에 삼성전자가 포함된 회사들에 대한 개황정보
dart.company_by_name('삼성전자')

# 삼성전자 사업보고서 (2018.12) 원문 텍스트
xml_text = dart.document('20190401004781')


# ==== 2. 사업보고서 ====
# 삼성전자(005930), 배당관련 사항, 2018년
dart.report('005930', '배당', 2018)

# 서울반도체(046890), 최대주주 관한 사항, 2018년
dart.report('046890', '최대주주', 2018)

# 서울반도체(046890), 임원 관한 사항, 2018년
dart.report('046890', '임원', 2018)

# 삼성바이오로직스(207940), 2019년, 소액주주에 관한 사항
dart.report('207940', '소액주주', '2019')


# ==== 3. 상장기업 재무정보 ====
# 삼성전자 2018 재무제표
dart.finstate('삼성전자', 2018) # 사업보고서

# 삼성전자 2018Q1 재무제표
dart.finstate('삼성전자', 2018, reprt_code='11013')

# 여러종목 한번에
dart.finstate('00126380,00164779,00164742', 2018)
dart.finstate('005930, 000660, 005380', 2018)
dart.finstate('삼성전자, SK하이닉스, 현대자동차', 2018)

# 단일기업 전체 재무제표 (삼성전자 2018 전체 재무제표)
dart.finstate_all('005930', 2018)

# 재무제표 XBRL 원본 파일 저장 (삼성전자 2018 사업보고서)
dart.finstate_xml('20190401004781', save_as='삼성전자_2018_사업보고서_XBRL.zip')

# XBRL 표준계정과목체계(계정과목)
dart.xbrl_taxonomy('BS1')


# ==== 4. 지분공시 ====
# 대량보유 상황보고 (종목코드, 종목명, 고유번호 모두 지정 가능)
dart.major_shareholders('삼성전자')

# 임원ㆍ주요주주 소유보고 (종목코드, 종목명, 고유번호 모두 지정 가능)
dart.major_shareholders_exec('005930')


# ==== 5. 확장 기능 ====
# 지정한 날짜의 공시목록 전체 (시간 정보 포함)`
dart.list_date_ex('2020-01-03')

# 개별 문서 제목과 URL
rcp_no = '20190401004781' # 삼성전자 2018년 사업보고서
dart.sub_docs(rcp_no)

# 제목이 잘 매치되는 순서로 소트
dart.sub_docs('20190401004781', match='사업의 내용')

# 첨부 문서 제목과 URL
dart.attach_doc_list(rcp_no)

# 제목이 잘 매치되는 순서로 소트
dart.attach_doc_list(rcp_no, match='감사보고서')

# 첨부 파일 제목과 URL
dart.attach_file_list(rcp_no)