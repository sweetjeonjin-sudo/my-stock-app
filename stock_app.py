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
        foreign_net = 0
        institution_net = 0
        count = 0
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) == 9 and count < 5:
                f_net = cols[6].get_text().replace(',', '').strip()
                i_net = cols[5].get_text().replace(',', '').strip()
                if f_net and i_net:
                    foreign_net += int(f_net)
                    institution_net += int(i_net)
                    count += 1
        return foreign_net, institution_net
    except:
        return 0, 0

# 2. 메인 데이터 수집 및 분석 함수 (에러 방어 강화)
@st.cache_data(ttl=600)
def fetch_combined_data():
    # 주소를 거래량 상위 페이지로 안정적으로 변경
    url = "https://finance.naver.com/sise/sise_quant.naver"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'cp949'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # [에러 방지] 테이블이 존재하는지 확인
        table = soup.find('table', class_='type_2')
        if table is None:
            return pd.DataFrame()
            
        rows = table.find_all('tr')
        stocks = []
        count = 0
        
        for row in rows:
            name_tag = row.select_one("a.tltle")
            if name_tag and count < 20:
                cols = row.find_all("td")
                if len(cols) < 7: continue
                
                name = name_tag.get_text().strip()
                price = int(cols[2].get_text().replace(',', ''))
                if price < 2000: continue # 동전주 필터링
                
                change_text = cols[4].get_text().strip()
                amount = int(cols[6].get_text().replace(',', '')) // 100
                code = name_tag['href'].split('=')[-1]
                
                f_net, i_net = fetch_investor_data(code)
                ticker = f"{code}.KS" if int(code) < 900000 else f"{code}.KQ"
                data = yf.download(ticker, period="3mo", interval="1d", progress=False)
                
                if not data.empty:
                    curr_p = float(data['Close'].iloc[-1])
                    high_p = float(np.max(data['High'].values))
                    low_p = float(np.min(data['Low'].values))
                    
                    pos = "중간"
                    if curr_p <= (low_p * 1.1): pos = "바닥"
                    elif curr_p >= (high_p * 0.93): pos = "고점"
                    
                    if pos == "바닥" and (f_net > 0 or i_net > 0): ai_final = "✅ 강력 매수"
                    elif pos == "바닥" and (f_net < 0 and i_net < 0): ai_final = "⏳ 매수 유보"
                    elif pos == "고점" and (f_net < 0 and i_net < 0): ai_final = "🚨 분할 매도"
                    elif pos == "고점" and (f_net > 0 and i_net > 0): ai_final = "🔥 불타기 가능"
                    else: ai_final = "➡️ 관망/보유"

                    stocks.append({
                        '종목명': name, 'AI결론': ai_final, '현재가': price, '등락': change_text, 
                        '거래대금(억)': amount, '코드': code, '상방': high_p, '하방': low_p,
                        '외인순매수': f_net, '기관순매수': i_net
                    })
                    count += 1
        return pd.DataFrame(stocks)
    except Exception as e:
        return pd.DataFrame()

# --- UI 레이아웃 ---
st.title("👨‍💼 2026 직장인 AI 투자 조수")
st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

df = fetch_combined_data()

if not df.empty:
    col_main, col_side = st.columns([1.1, 0.9])

    with col_main:
        st.subheader("💎 수급 및 추세 통합 리스트")
        event = st.dataframe(
            df[['종목명', 'AI결론', '등락', '거래대금(억)']],
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row"
        )
        st.write("👆 종목을 클릭하면 오른쪽 가이드가 나타납니다.")

    with col_side:
        idx = event.selection.rows[0] if event.selection.rows else 0
        target = df.iloc[idx]
        
        st.subheader(f"🔍 {target['종목명']} 투자 가이드")
        st.markdown(f"## **{target['AI결론']}**")
        
        if "강력 매수" in target['AI결론']:
            st.success("✅ **가격도 싼데 큰손(외인/기관)들이 담고 있습니다.** 가장 안전하고 수익 확률이 높은 최고의 자리입니다!")
        elif "매수 유보" in target['AI결론']:
            st.warning("⏳ **가격은 싸지만 큰손들이 계속 팔고 있습니다.** 아직 '지하실'이 더 있을 수 있으니 기다리세요.")
        elif "분할 매도" in target['AI결론']:
            st.error("🚨 **가격이 높은데 큰손들이 수익 실현 중입니다.** 수익을 챙길 타이밍입니다.")
        elif "불타기 가능" in target['AI결론']:
            st.info("🔥 **전고점 돌파 구간에서 큰손들이 더 사고 있습니다.** 추가 상승이 기대되는 구간입니다.")
        else:
            st.info("➡️ 현재 뚜렷한 특징이 없는 구간입니다. 관망을 권장합니다.")

        # 차트 시각화
        data_target = yf.download(f"{target['코드']}.KS" if int(target['코드']) < 900000 else f"{target['코드']}.KQ", period="3mo", interval="1d", progress=False)
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(data_target.index, data_target['Close'], color='#1f77b4', linewidth=2)
        ax.axhline(target['상방'], color='red', linestyle='--', alpha=0.5, label='고점')
        ax.axhline(target['하방'], color='green', linestyle='--', alpha=0.5, label='바닥')
        ax.legend()
        st.pyplot(fig)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("현재가", f"{target['현재가']:,.0f}원")
        c2.metric("외인(5일)", f"{target['외인순매수']:,.0f}")
        c3.metric("기관(5일)", f"{target['기관순매수']:,.0f}")
        
        st.link_button(f"📰 {target['종목명']} 뉴스 보기", f"https://search.naver.com/search.naver?query={target['종목명']}", use_container_width=True)
else:
    st.error("네이버 서버 연결이 일시적으로 원활하지 않습니다. 1~2분 후 다시 시도해 주세요.")
    if st.button("새로고침"):
        st.rerun()