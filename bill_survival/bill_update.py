import sqlite3
import requests
import pandas as pd
import xmltodict
import json
import numpy as np

#법안 정보 가져오기
MYKEY2 = "sh1BLNic10zE0pynUHLuP0%2FDxTd5Fi4m5%2B4CojHK%2B%2BXTxH9ykyO3yVPROWHp3zsR9%2BB38%2BkIGmWgHB%2BYfmUB6A%3D%3D"

start_date = '2020-06-01'
end_date = '2021-01-23'
url = f"http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList?ord=21&start_propose_date={start_date}&end_propose_date={end_date}&numOfRows=9000&ServiceKey=" + MYKEY2

req = requests.get(url)
xpars = xmltodict.parse(req.text)

jsonDump = json.dumps(xpars)
jsonBody = json.loads(jsonDump)

bill_df = pd.DataFrame(jsonBody['response']['body']['items']['item'])

bill_df = bill_df[bill_df['passGubn']=='계류의안']

#법안 위원회 상정일 가져오기
MYKEY2 = "sh1BLNic10zE0pynUHLuP0%2FDxTd5Fi4m5%2B4CojHK%2B%2BXTxH9ykyO3yVPROWHp3zsR9%2BB38%2BkIGmWgHB%2BYfmUB6A%3D%3D"

presentDt = []

for idx in bill_df['billId']:

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


bill_df['presentDt'] = presentDt



data = bill_df[['presentDt', 'billId']]
data = [tuple(x) for x in data.to_numpy()]

#계류의안만 update하기
conn = sqlite3.connect("bills.db", isolation_level=None)
cursor = conn.cursor()

sql = 'UPDATE bills_2021 SET presentDt=? WHERE billId=?'
cursor.executemany(sql, data)
conn.commit()
conn.close()
