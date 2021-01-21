import re
import numpy as np
import pandas as pd
import pickle
import sqlite3
from eunjeon import Mecab
from gensim.models import Word2Vec as w2v
from sklearn.feature_extraction.text import CountVectorizer

#21대 국회 법안 데이터 전처리
conn = sqlite3.connect("bills.db")
#df = pd.read_sql("select * from bills_2021 where proposeDt >= '2021-01-01'", con=conn)
cursor = conn.cursor()

cursor.execute('select * from bills_2021')

rows = cursor.fetchall()
cols = [column[0] for column in cursor.description]

df = pd.DataFrame.from_records(data=rows, columns=cols)

conn.close()

#가결/부결 코딩

for i in range(len(df)):
    if df.loc[i, 'generalResult'] == '대안반영폐기' or df.loc[i, 'generalResult'] == '수정가결' or df.loc[i, 'generalResult'] == '원안가결':
        df.loc[i, 'result'] = 1
    elif df.loc[i, 'generalResult'] == '철회' or df.loc[i, 'generalResult'] == '폐기' or df.loc[i, 'generalResult'] == '부결':
        df.loc[i, 'result'] = 0
    else:
        df.loc[i, 'result'] = 0

# 소관위 원-핫코딩
committee_set = list(set(df['COMMITTEE']))
if None in committee_set:
    committee_set.remove(None)

committee = []
for com in committee_set:
    coms = com.split(", ")
    for c in coms:
        committee.append(c)

committee = list(set(committee))

for i in range(len(df)):
    if df['COMMITTEE'][i] != None:
        if df['COMMITTEE'][i].__contains__('특별위원회'):
            df.loc[i, '특별위원회'] = 1
        for com in committee:
            if df['COMMITTEE'][i].__contains__(com):
                df.loc[i, com] = 1
            else:
                df.loc[i, com] = 0
    else:
        df.loc[i, '특별위원회'] = 0
        for com in committee:
            df.loc[i, com] = 0


for i in range(len(df)):
    if df.loc[i, 'polyNm'] == '더불어민주당' or df.loc[i, 'polyNm'] == '열린민주당':
        df.loc[i, 'party'] = 0
    elif df.loc[i, 'polyNm'] == '국민의힘' or df.loc[i, 'polyNm'] == '미래통합당' :
        df.loc[i, 'party'] = 1
    elif df.loc[i, 'polyNm'] == '국민의당' or df.loc[i, 'polyNm'] == '기본소득당' or df.loc[i, 'polyNm'] == '시대전환' or df.loc[i, 'polyNm'] == '정의당':
        df.loc[i, 'party'] = 2
    else:
        df.loc[i, 'party'] = 3

for i in range(len(df)):
    if df.loc[i, 'proposerKind'] == '위원장':
        df.loc[i, 'RST_PROPOSER'] = '위원장'
        df.loc[i, 'party'] = 4
    elif df.loc[i, 'proposerKind'] == '의장':
        df.loc[i, 'RST_PROPOSER'] = '의장'
        df.loc[i, 'party'] = 4
    elif df.loc[i, 'proposerKind'] == '정부':
        df.loc[i, 'RST_PROPOSER'] = '정부'
        df.loc[i, 'party'] = 5


for i in range(len(df)):
    if df.loc[i, 'polyNm'] == '더불어민주당' or df.loc[i, 'polyNm'] == '열린민주당':
        df.loc[i, 'num_seats'] = 185
    elif df.loc[i, 'polyNm'] == '국민의힘':
        df.loc[i, 'num_seats'] = 103
    elif df.loc[i, 'polyNm'] == '미래통합당':
        df.loc[i, 'num_seats'] = 84
    elif df.loc[i, 'polyNm'] == '정의당' or df.loc[i, 'polyNm'] == '기본소득당' or df.loc[i, 'polyNm'] == '시대전환':
        df.loc[i, 'num_seats'] = 185
    elif df.loc[i, 'polyNm'] == '국민의당':
        df.loc[i, 'num_seats'] = 3
    elif df.loc[i, 'polyNm'] == '무소속':
        df.loc[i, 'num_seats'] = 9


for i in range(len(df)):
    if df.loc[i, 'billName'].__contains__('전부개정법률안'):
        df.loc[i, '입법형태'] = '전부개정'
    elif df.loc[i, 'billName'].__contains__('일부개정법률안'):
        df.loc[i, '입법형태'] = '일부개정법률안'
    else:
        df.loc[i, '입법형태'] = '제정'

# 법안별 주요내용이 26개 카테고리 주제와 얼마나 유사한지 유사도 계산

model = w2v.load('word2vec.model')  # 모델 불러오기

tagger = Mecab()

summary_re = []
for text in df['summary']:
    try:
        summary_re.append(re.sub('[^가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z]', ' ', text))
    except:
        summary_re.append('NaN')

cnt_words = []
summary_re3 = []

for text in summary_re:
    pos_text = tagger.pos(text)
    word_list = []
    for word in pos_text:
        word_list.append(word[0])
    cnt_words.append(len(word_list) + 1)
    summary_re3.append(' '.join(word_list))

df['summary_re'] = summary_re3

words = list()
for word in model.wv.vocab:
    words.append(word)

# 주제 카테고리 dic
category = {'국회': ['의회', '국회'],
            '정당/선거': ['정당', '선거'],
            '안보': ['군사', '안보', '북한'],
            '사법': ['사법', '법원', '검찰', '소송'],
            '행정': ['행정', '지자체', '자치', '경찰', '공무원'],
            '재정': ['재정', '예산', '회계'],
            '중소기업': ['중소기업', '창업', '벤처', '스타트업'],
            '에너지': ['에너지', '수소', '전기', '가스'],
            '부동산': ['주택', '부동산', '주거', '임대차'],
            '금융': ['금융', '투자', '자본', '보험업'],
            '자동차': ['자동차', '승합자동차', '이륜자동차', '승용차'],
            '건설/기계/조선': ['기계', '건설업', '건설사', '건축', '조선업', '해운업', '발주'],
            '유통/무역': ['유통', '물류', '무역', '쇼핑몰', '마트', '백화점'],
            'IT': ['IT', '통신', '게임', '데이터', '인공지능', '블록체인', '클라우드'],
            '농축산': ['농업', '축산', '수산'],
            '복지': ['복지', '연금', '빈곤', '수당'],
            '의료/보건': ['의료', '보건', '병원', '질병', '의약품'],
            '도시/교통': ['도시', '교통', '운전', '도로'],
            '교육': ['교육', '학교', '대학', '유치원', '입시'],
            '환경': ['친환경', '오염', '저탄소', '온실가스', '기후', '수자원'],
            '노동': ['노동', '임금', '노동조합', '퇴직', '채용', '근로'],
            '치안/안전': ['치안', '범죄', '안전', '사고', '소방', '형사'],
            '가족': ['가족', '아동', '청소년'],
            '여성': ['여성', '출산', '육아', '성범죄', '성희롱'],
            '예체능': ['예술', '영화', '음악', '전시', '공연', '문화재', '체육', '방송', '언론', '스포츠', '콘텐츠']
            }

for key in category.keys():
    keyword_similar = np.zeros(shape=(len(words),))

    for keyword in category[key]:
        keyword_similar_2 = []
        for word in words:
            sm = model.wv.similarity(keyword, word)
            if sm >= 0.8:
                keyword_similar_2.append(sm)
            else:
                keyword_similar_2.append(0)

        keyword_similar_2 = np.asarray(keyword_similar_2)
        keyword_similar += keyword_similar_2

    keyword_similar = list(keyword_similar)
    keyword_similar_df = pd.DataFrame({'words': words, 'similar': keyword_similar})
    keyword_similar_df = keyword_similar_df.sort_values(by=['words'], axis=0)
    keyword_similar_df = keyword_similar_df.set_index('words')
    keyword_similar_df = keyword_similar_df.T

    vectorizer = CountVectorizer(vocabulary=keyword_similar_df.columns, binary=False)
    X = vectorizer.fit_transform(summary_re3)
    words_df = pd.DataFrame(X.toarray(), columns=vectorizer.get_feature_names())
    words_df = words_df.T

    tdm = np.dot(keyword_similar_df, words_df)
    tdm = tdm.T
    tdm = np.ravel(tdm)  # 2차원 배열을 1차원으로 평평하게 만듬
    df[key] = list(tdm / cnt_words)


#상임위 상정 여부 변수

for i in range(len(df)):
    if df.loc[i, 'presentDt'] == 'None':
        df.loc[i, '상임위 상정 여부'] = 0
    elif df.loc[i, 'presentDt'] == None:
        df.loc[i, '상임위 상정 여부'] = 0
    else:
        df.loc[i, '상임위 상정 여부'] = 1


df = df.rename(columns={'billId':'법안코드',
                        'billName':'법안명',
                        'result':'처리구분',
                        'RST_PROPOSER':'제안자',
                        'diversity':'정당다양성',
                        'proposeDt':'접수일자'})

df['반대당발언횟수']=0

df = df[['법안코드', '법안명', 'billNo', 'passGubn', 'procStageCd',
 '접수일자', 'proposerKind', 'summary', 'generalResult', 'procDt', 'index',
 '공동발의자수','공동발의평균선수', '정당다양성', 'presentDt',
 'COMMITTEE', 'PROC_RESULT', '제안자', 'PUBL_PROPOSER', 'COMMITTEE_ID', 'polyNm',
 '당선횟수', '선출형태', '처리구분', '특별위원회',
 '환경노동위원회', '여성가족위원회', '법제사법위원회', '농림축산식품해양수산위원회',
 '기획재정위원회', '국방위원회', '과학기술정보방송통신위원회',
 '산업통상자원중소벤처기업위원회', '국토교통위원회', '행정안전위원회',
 '보건복지위원회', '문화체육관광위원회','교육위원회','외교통일위원회',
 '정무위원회','국회운영위원회','party', 'num_seats', '입법형태',
 'summary_re', '국회', '정당/선거', '안보', '사법', '행정', '재정', '중소기업', '에너지', '부동산', '금융',
 '자동차', '건설/기계/조선', '유통/무역', 'IT', '농축산', '복지', '의료/보건', '도시/교통',
 '교육', '환경', '노동','치안/안전', '가족', '여성', '예체능', '상임위 상정 여부', '반대당발언횟수']]



print(df.columns)


conn = sqlite3.connect("bills_preprocessed.db", isolation_level=None)

cursor = conn.cursor()


cursor.execute('CREATE TABLE IF NOT EXISTS bills (법안코드 text PRIMARY KEY, 법안명 text, billNo text, passGubn text,\
 procStageCd text, 접수일자 text, proposerKind text, summary text, generalResult text, procDt text, "index" INTEGER, \
 공동발의자수 INTEGER, 공동발의평균선수 real, 정당다양성 integer, presentDt text, COMMITTEE text, PROC_RESULT text, 제안자 text, \
 PUBL_PROPOSER text, COMMITTEE_ID integer, polyNm text, 당선횟수 integer, 선출형태 text, \
 처리구분 text, 특별위원회 integer, 환경노동위원회 integer ,여성가족위원회 integer, 법제사법위원회 integer, 농림축산식품해양수산위원회 integer, \
 기획재정위원회 integer, 국방위원회 integer,  과학기술정보방송통신위원회 integer, 산업통상자원중소벤처기업위원회 integer, \
 국토교통위원회 integer, 행정안전위원회 integer, 보건복지위원회 integer, 문화체육관광위원회 integer, 교육위원회 integer, \
 외교통일위원회 integer, 정무위원회 integer, 국회운영위원회 integer, party integer, num_seats integer, 입법형태 text, summary_re text, 국회 real, "정당/선거" real,\
 안보 real, 사법 real, 행정 real, 재정 real, 중소기업 real, 에너지 real, 부동산 real, 금융 real, 자동차 real, "건설/기계/조선" real, "유통/무역" real, IT real,\
 농축산 real, 복지 real, "의료/보건" real, "도시/교통" real, 교육 real, 환경 real, 노동 real, "치안/안전" real, 가족 real, 여성 real, 예체능 real, \
 "상임위 상정 여부" real, 반대당발언횟수 real)')

data = [tuple(x) for x in df.to_numpy()]


for row in data:
    check = cursor.execute('SELECT EXISTS (select 1 from bills where 법안코드=?)', (row[0],))
    if check.fetchall()[0][0] == 1:
        cursor.execute('UPDATE bills SET "상임위 상정 여부"=? WHERE 법안코드=?', (row[70], row[0]))
    else:
        sql = 'INSERT INTO bills VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, \
                                        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
        cursor.execute(sql, row)


conn.commit()
conn.close()

#df.to_sql('bills', conn)
