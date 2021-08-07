import pandas as pd
import OpenDartReader
import sqlite3

con = sqlite3.connect('finance.db')
cur = con.cursor()
cur.execute('CREATE TABLE stocks')

# ==== 0. 객체 생성 ====
# 객체 생성 (API KEY 지정)
api_key = '030931185c55a687211970bb072de0382b4a0ffd'

dart = OpenDartReader(api_key)


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