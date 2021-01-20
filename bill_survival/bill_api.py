import sqlite3
import requests
import pandas as pd
import xmltodict
import json
import numpy as np

#법안 정보 가져오기
mykey = "f9191bcb5fc3472890a5e84347ae5ebb"
MYKEY2 = "sh1BLNic10zE0pynUHLuP0%2FDxTd5Fi4m5%2B4CojHK%2B%2BXTxH9ykyO3yVPROWHp3zsR9%2BB38%2BkIGmWgHB%2BYfmUB6A%3D%3D"

start_date = '2020-09-01'
end_date = '2020-09-30'
url = f"http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList?ord=21&start_propose_date={start_date}&end_propose_date={end_date}&numOfRows=9000&ServiceKey=" + MYKEY2

req = requests.get(url)
xpars = xmltodict.parse(req.text)

jsonDump = json.dumps(xpars)
jsonBody = json.loads(jsonDump)

bill_df = pd.DataFrame(jsonBody['response']['body']['items']['item'])

if 'procDt' not in bill_df.columns:
    bill_df['procDt'] = None
if 'generalResult' not in bill_df.columns:
    bill_df['generalResult'] = None

print('법안 정보 가져오기')

#21대 국회의원 목록

url3 = f"https://open.assembly.go.kr/portal/openapi/nwvrqwxyaytdsfvhu?KEY={mykey}&Type=json&pSize=300"
req = requests.get(url3).json()
congressman = pd.DataFrame(req['nwvrqwxyaytdsfvhu'][1]['row'])

for i in range(len(congressman)):
    congressman.loc[i, '당선횟수'] = len(congressman.loc[i, 'UNITS'].split(', '))

print('국회의원 목록 가져오기 성공')

# 공동발의
cobill = pd.DataFrame()

for bill_id in bill_df['billId']:

    url2 = f"http://apis.data.go.kr/9710000/BillInfoService2/getBillPetitionMemberList?gbn1=bill&gbn2=reception&bill_id={bill_id}&ServiceKey=" + MYKEY2

    req = requests.get(url2)
    xpars = xmltodict.parse(req.text)

    jsonDump = json.dumps(xpars)
    jsonBody = json.loads(jsonDump)

    try:
        cobill_sub = pd.DataFrame(jsonBody['response']['body']['items']['item'])
    except:
        pass
    else:
        cobill_sub['billId'] = bill_id
        cobill = pd.concat([cobill, cobill_sub])


cobill = cobill.reset_index()
for i in range(len(cobill)):
    if cobill.loc[i, 'polyNm'] == '미래통합당':
        cobill.loc[i, 'polyNm'] = '국민의힘'


congressman_re = congressman[['HJ_NM', 'POLY_NM', '당선횟수', 'ELECT_GBN_NM']]
congressman_re = congressman_re.rename(columns={'HJ_NM': 'hjNm', 'POLY_NM':'polyNm', 'ELECT_GBN_NM':'선출형태'})
cobill = pd.merge(cobill, congressman_re, how='left', on=['hjNm', 'polyNm'])

for i in range(len(cobill)):
    if cobill.loc[i, 'memName'] == '김병욱' and cobill.loc[i, 'polyNm'] == '국민의힘':
        cobill.loc[i, '당선횟수'] = 1
        cobill.loc[i, '선출형태'] = '지역구'
    if cobill.loc[i, 'memName'] == '전봉민':
        cobill.loc[i, '당선횟수'] = 1
        cobill.loc[i, '선출형태'] = '지역구'
    if cobill.loc[i, 'memName'] == '박덕훔':
        cobill.loc[i, '당선횟수'] = 3
        cobill.loc[i, '선출형태'] = '지역구'
    if cobill.loc[i, 'memName'] == '김홍걸':
        cobill.loc[i, '당선횟수'] = 1
        cobill.loc[i, '선출형태'] = '비례대표'

print(cobill.columns)

spon_avg_elected = cobill.pivot_table(index='billId', values='당선횟수', aggfunc=np.mean).reset_index()

spon = cobill.pivot_table(index='billId', values='gbn1', aggfunc='count') #공동발의 의원수
spon = spon.sort_values('billId')
spon = pd.merge(spon, spon_avg_elected, how='left', on='billId')
spon = spon.rename(columns={'당선횟수':'공동발의평균선수'})

print('공동발의 데이터 가져옴')

diversity = []  # 정당다양성

bill_set = list(set(cobill['billId']))
bill_set.sort()

for idx in bill_set:
    subset = cobill[cobill['billId'] == idx]
    if len(set(subset['polyNm'])) >= 2:
        diversity.append(1)
    else:
        diversity.append(0)

spon['diversity'] = diversity

spon = spon.reset_index()
spon = spon.rename(columns={'gbn1':'공동발의자수','정당다양성':'diversity'})

df = pd.merge(bill_df, spon, how='left', on='billId')
print(df.columns)

print('공동발의 데이터 가져옴2')

#법안 위원회 상정일 가져오기
MYKEY2 = "sh1BLNic10zE0pynUHLuP0%2FDxTd5Fi4m5%2B4CojHK%2B%2BXTxH9ykyO3yVPROWHp3zsR9%2BB38%2BkIGmWgHB%2BYfmUB6A%3D%3D"

presentDt = []

for idx in df['billId']:

    url = f"http://apis.data.go.kr/9710000/BillInfoService2/getBillCommissionExaminationInfo?bill_id={idx}&ServiceKey=" + MYKEY2
    req = requests.get(url)
    xpars = xmltodict.parse(req.text)

    jsonDump = json.dumps(xpars)
    jsonBody = json.loads(jsonDump)

    try:
        item = jsonBody['response']['body']['JurisdictionExamination']['item']
    except:
        presentDt.append('None')
    else:
        if len(item) == 3:
            if item[0]['presentDt'] != None:
                presentDt.append(item[0]['presentDt'])
            elif item[1]['presentDt'] != None:
                presentDt.append(item[1]['presentDt'])
            else:
                presentDt.append(item[2]['presentDt'])
        elif len(item) == 2:
            if item[0]['presentDt'] != None:
                presentDt.append(item[0]['presentDt'])
            else:
                presentDt.append(item[1]['presentDt'])
        else:
            try:
                dt = jsonBody['response']['body']['JurisdictionExamination']['item']['presentDt'] #submitDt: 위원회 회부일, presentDt: 위원회 상정일, procDt: 위원회 처리일
                presentDt.append(dt)
            except:
                presentDt.append('None')


df['presentDt'] = presentDt

print('상정일 가져옴')
#법안별 소관위 정보, 대표발의자 정보 등 가져오기

df2 = pd.DataFrame()

for bill_id in df['billId']:
    bill_id = str(bill_id)
    url2 = f"https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn?BILL_ID={bill_id}&KEY={mykey}&AGE=21&Type=json"
    req = requests.get(url2).json()
    try:
        df2 = pd.concat([df2, pd.DataFrame(req['nzmimeepazxkubdpn'][1]['row'])])
    except:
        pass

df3 = df2[['BILL_ID', 'COMMITTEE', 'PROC_RESULT', 'RST_PROPOSER', 'PUBL_PROPOSER', 'COMMITTEE_ID']]
df3 = df3.rename(columns={'BILL_ID': 'billId'})
df = pd.merge(df, df3, how='left', on='billId')

print('소관위, 대표발의자 merge')

#대표발의자 정당 merge
cobill = cobill.rename(columns={'memName': 'RST_PROPOSER'})
df_re = df[['billId', 'RST_PROPOSER']]
df_re = pd.merge(df_re, cobill, how='left', on=['billId', 'RST_PROPOSER'])

df_re = df_re[['billId', 'polyNm', '당선횟수', '선출형태']]
df = pd.merge(df, df_re, how='left', on='billId')

print('대표발의자 정당merge')

#이수진 의원 동명이인 처리
MYKEY2 = "sh1BLNic10zE0pynUHLuP0%2FDxTd5Fi4m5%2B4CojHK%2B%2BXTxH9ykyO3yVPROWHp3zsR9%2BB38%2BkIGmWgHB%2BYfmUB6A%3D%3D"

hjnm = '李秀眞'  #서울 동작구을
check='G01'
url_sujin = f"http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList?gbn=dae_num_name&ord=21&mem_name_check={check}&hj_nm={hjnm}&start_propose_date=2020-12-01&end_propose_date=2020-12-31&numOfRows=9000&ServiceKey=" + MYKEY2

req_re = requests.get(url_sujin)
xpars = xmltodict.parse(req_re.text)

jsonDump = json.dumps(xpars)
jsonBody = json.loads(jsonDump)

sujin1 = pd.DataFrame(jsonBody['response']['body']['items']['item'])

hjnm2 = '李壽珍' #비례대표
check='G01'
url_sujin2 = f"http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList?gbn=dae_num_name&ord=21&mem_name_check={check}&hj_nm={hjnm2}&start_propose_date=2020-12-01&end_propose_date=2020-12-31&numOfRows=9000&ServiceKey=" + MYKEY2

req_re = requests.get(url_sujin2)
xpars = xmltodict.parse(req_re.text)

jsonDump = json.dumps(xpars)
jsonBody = json.loads(jsonDump)

sujin2 = pd.DataFrame(jsonBody['response']['body']['items']['item'])

ids_sujin1 = list(sujin1['billId'])
ids_sujin2 = list(sujin2['billId'])

for i in range(len(df)):
    if df.loc[i, 'billId'] in ids_sujin1:
        df.loc[i, '선출형태'] = '지역구'
    elif df.loc[i, 'billId'] in ids_sujin2:
        df.loc[i, '선출형태'] = '비례대표'

df = df.drop_duplicates()

if 'level_0' in df.columns:
    del df['level_0']


conn = sqlite3.connect("bills.db", isolation_level=None)

#df.to_sql('bills_2021', conn)

cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS bills_2021 (billId text PRIMARY KEY, billName text, billNo text, passGubn text,\
 procStageCd text, proposeDt text, proposerKind text, summary text, generalResult text, procDt text, "index" INTEGER, \
 공동발의자수 INTEGER, 공동발의평균선수 real, diversity integer, presentDt text, COMMITTEE text, PROC_RESULT text, RST_PROPOSER text, \
 PUBL_PROPOSER text, COMMITTEE_ID integer, polyNm text, 당선횟수 integer, 선출형태 text)')

data = [tuple(x) for x in df.to_numpy()]

for row in data:
    check = cursor.execute('SELECT EXISTS (select 1 from bills_2021 where billId=?)', (row[0],))
    if check.fetchall()[0][0] == 1:
        pass
    else:
        sql = 'INSERT INTO bills_2021 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
        cursor.execute(sql, row)

conn.commit()
conn.close()

