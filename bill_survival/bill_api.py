import sqlite3
import requests
import pandas as pd
import xmltodict
import json
import numpy as np

#법안 정보 가져오기
mykey = "f9191bcb5fc3472890a5e84347ae5ebb"
MYKEY2 = "sh1BLNic10zE0pynUHLuP0%2FDxTd5Fi4m5%2B4CojHK%2B%2BXTxH9ykyO3yVPROWHp3zsR9%2BB38%2BkIGmWgHB%2BYfmUB6A%3D%3D"

url = f"http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList?ord=21&start_propose_date=2021-01-01&end_propose_date=2021-01-11&numOfRows=9000&ServiceKey=" + MYKEY2

req = requests.get(url)
xpars = xmltodict.parse(req.text)

jsonDump = json.dumps(xpars)
jsonBody = json.loads(jsonDump)

bill_df = pd.DataFrame(jsonBody['response']['body']['items']['item'])

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


congressman_re = congressman[['HG_NM', 'POLY_NM', '당선횟수', 'ELECT_GBN_NM']]
congressman_re = congressman_re.rename(columns = {'HG_NM': 'memName', 'POLY_NM':'polyNm', 'ELECT_GBN_NM':'선출형태'})
cobill = pd.merge(cobill, congressman_re, how='left', on=['memName', 'polyNm'])

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

print('소관위 대표발의자 merge')

#대표발의자 정당 merge
cobill = cobill.rename(columns={'memName': 'RST_PROPOSER'})
df_re = df[['billId', 'RST_PROPOSER']]
df_re = pd.merge(df_re, cobill, how='left', on=['billId', 'RST_PROPOSER'])

df_re = df_re[['billId', 'polyNm', '당선횟수', '선출형태']]
df = pd.merge(df, df_re, how='left', on='billId')

print('대표발의자 정당merge')

conn = sqlite3.connect("bills.db", isolation_level=None)
df.to_sql('bills_2021', conn)
