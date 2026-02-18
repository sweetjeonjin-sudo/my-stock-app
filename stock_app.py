import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

# 페이지 설정
st.set_page_config(page_title="2026 직장인 AI 투자 조수", layout="wide")

# 1. 외국인/기관 수급 데이터 수집 함수
def fetch_investor_data(code):
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select("table.type2 tr")
        f_net, i_net, count = 0, 0, 0
        for row in rows:
            cols = row.find_all("td")
            if len(cols) == 9 and count < 5:
                fn = cols[6].get_text().replace(',', '').strip()
                in_ = cols[5].get_text().replace(',', '').strip()
                if fn and in_:
                    f_net += int(fn); i_net += int(in_); count += 1
        return f_net, i_net
    except: return 0, 0

# 2. 분석 핵심 로직 (상세 가이드 포함)
def analyze_stock_logic(code, name="검색종목"):
    ticker = f"{code}.KS" if int(code) < 900000 else f"{code}.KQ"
    data = yf.download(ticker, period="3mo", interval="1d", progress=False)
    if data.empty: return None
    
    f_net, i_net = fetch_investor_data(code)
    curr_p = float(data['Close'].iloc[-1].item()) if hasattr(data['Close'].iloc[-1], 'item') else float(data['Close'].iloc[-1])
    high_p = float(np.max(data['High'].values))
    low_p = float(np.min(data['Low'].values))
    
    pos = "중간"
    if curr_p <= (low_p * 1.1): pos = "바닥"
    elif curr_p >= (high_p * 0.93): pos = "고점"
    
    if pos == "바닥" and (f_net > 0 or i_net > 0):
        ai_key = "✅ 강력 매수"
        ai_desc = "✅ 강력 매수 (바닥권 + 외인/기관 동반 매수): 가격도 싼데 큰손들이 담고 있다면 신뢰도가 매우 높습니다. (직장인에게 최고의 자리)"
    elif pos == "바닥" and (f_net < 0 and i_net < 0):
        ai_key = "⏳ 매수 유보"
        ai_desc = "⏳ 매수 유보 (바닥권 + 외인/기관 매도): 가격은 싸지만 큰손들이 계속 팔고 있다면, '지하실'이 더 있을 수 있으니 기다려야 합니다."
    elif pos == "고점" and (f_net < 0 and i_net < 0):
        ai_key = "🚨 분할 매도"
        ai_desc = "🚨 분할 매도 (고점권 + 외인/기관 매도): 가격도 높은데 큰손들이 수익 실현 중이라면 탈출 신호입니다."
    elif pos == "고점" and (f_net > 0 and i_net > 0):
        ai_key = "🔥 불타기 가능"
        ai_desc = "🔥 불타기 가능 (고점권 + 외인/기관 매수): 전고점 돌파형으로, 강력한 추가 상승이 예상되는 구간입니다."
    else:
        ai_key = "➡️ 관망/보유"
        ai_desc = "➡️ 관망/보유: 현재 뚜렷한 매수/매도 특징이 없는 중간 구간입니다. 기존 계획대로 유지하세요."
    
    return {
        '종목명': name, 'AI결론': ai_key, '상세가이드': ai_desc, '현재가': curr_p, 
        '코드': code, '상방': high_p, '하방': low_p,
        '외인순매수': f_net, '기관순매수': i_net, 'data': data
    }

# 3. 데이터 수집
@st.cache_data(ttl=600)
def fetch_combined_data():
    url = "https://finance.naver.com/sise/sise_quant.naver"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        res.encoding = 'cp949'
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table', class_='type_2')
        if not table: return pd.DataFrame()
        stocks = []
        rows = table.find_all('tr')
        count = 0
        for row in rows:
            name_tag = row.select_one("a.tltle")
            if name_tag and count < 15:
                cols = row.find_all("td")
                name = name_tag.get_text().strip()
                code = name_tag['href'].split('=')[-1]
                res_ana = analyze_stock_logic(code, name)
                if res_ana:
                    res_ana['등락'] = cols[4].get_text().strip()
                    res_ana['거래대금'] = int(cols[6].get_text().replace(',', '')) // 100
                    stocks.append(res_ana)
                    count += 1
        return pd.DataFrame(stocks)
    except: return pd.DataFrame()

# --- UI 레이아웃 ---
st.title("👨‍💼 2026 직장인 AI 투자 조수")

with st.sidebar:
    st.header("🔍 개별 종목 검색")
    search_code = st.text_input("종목코드 6자리를 입력하세요", placeholder="예: 005930")
    search_btn = st.button("AI 분석하기")

df = fetch_combined_data()

# 검색창 로직
if search_btn and search_code:
    st.divider()
    with st.spinner(f'코드 {search_code} 분석 중...'):
        s_res = analyze_stock_logic(search_code, f"검색({search_code})")
        if s_res:
            st.error(f"🎯 분석 결과: {s_res['상세가이드']}")
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.plot(s_res['data'].index, s_res['data']['Close'], color='orange')
            ax.axhline(s_res['상방'], color='red', linestyle='--', alpha=0.5)
            ax.axhline(s_res['하방'], color='green', linestyle='--', alpha=0.5)
            st.pyplot(fig)
        else: st.error("종목 코드를 확인해주세요.")

st.divider()

if not df.empty:
    col_l, col_r = st.columns([1.1, 0.9], gap="large")
    with col_l:
        st.subheader("🔥 실시간 주도주 분석표")
        display_df = df[['종목명', 'AI결론', '현재가', '등락', '거래대금']].copy()
        # 표시용 현재가 포맷팅
        display_df['현재가'] = display_df['현재가'].apply(lambda x: f"{int(x):,}")
        
        event = st.dataframe(display_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
    
    with col_r:
        idx = event.selection.rows[0] if event.selection.rows else 0
        target = df.iloc[idx]
        st.subheader(f"🔍 {target['종목명']} 투자 리포트")
        
        if "강력 매수" in target['AI결론']: st.success(target['상세가이드'])
        elif "매수 유보" in target['AI결론']: st.warning(target['상세가이드'])
        elif "분할 매도" in target['AI결론']: st.error(target['상세가이드'])
        elif "불타기 가능" in target['AI결론']: st.info(target['상세가이드'])
        else: st.write(target['상세가이드'])
        
        # 차트 출력 부분 (오류가 났던 곳 수정 완료)
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(target['data'].index, target['data']['Close'], color='#1f77b4', linewidth=2)
        ax.axhline(target['상방'], color='red', linestyle='--', alpha=0.5, label='고점')
        ax.axhline(target['하방'], color='green', linestyle='--', alpha=0.5, label='바닥')
        ax.legend(); ax.grid(alpha=0.2)
        st.pyplot(fig)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("현재가", f"{target['현재가']:,.0f}원")
        c2.metric("외인(5일)", f"{target['외인순매수']:,.0f}")
        c3.metric("기관(5일)", f"{target['기관순매수']:,.0f}")
        st.link_button(f"📰 뉴스 보기", f"https://search.naver.com/search.naver?query={target['종목명']}", use_container_width=True)
else:
    st.error("데이터 수집 중입니다. 새로고침을 해주세요.")