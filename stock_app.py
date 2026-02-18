import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="2026 돈의 흐름 스캐너", layout="wide")

# 데이터를 긁어와서 분석하는 핵심 함수
def fetch_market_data():
    url = "https://finance.naver.com/sise/sise_quant.naver"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.text, 'html.parser')
    
    stocks = []
    rows = soup.select("table.type_2 tr")
    
    for row in rows:
        name_tag = row.select_one("a.tltle")
        if name_tag:
            cols = row.select("td")
            name = name_tag.get_text()
            price = int(cols[2].get_text().replace(',', ''))
            change_percent = cols[4].get_text().strip()
            volume = int(cols[5].get_text().replace(',', ''))
            
            # 거래대금 계산 (억 단위)
            amount_total = (price * volume) // 100000000
            
            news_link = f"https://search.naver.com/search.naver?where=news&query={name}"
            linked_name = f'<a href="{news_link}" target="_blank" style="text-decoration:none; color:#1f77b4; font-weight:bold;">{name}</a>'
            
            stocks.append({
                '종목명': linked_name,
                '현재가': f"{price:,}원",
                '등락률': change_percent,
                '거래량': volume,
                '거래대금(억)': amount_total
            })
            
    return pd.DataFrame(stocks)

# --- 화면 UI 구성 ---
st.title("💰 2026 오전 10시 실시간 마켓 스캐너")
st.write(f"조회 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if st.button('🚀 실시간 데이터 동기화'):
    with st.spinner('시장의 모든 돈을 추적 중...'):
        all_data = fetch_market_data()
        
        # 화면을 왼쪽(col1)과 오른쪽(col2)으로 나눕니다
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 거래량 상위 (주수 기준)")
            st.caption("단순히 거래가 빈번한 순서입니다.")
            # 거래량 순서대로 상위 15개
            df_volume = all_data.sort_values(by='거래량', ascending=False).head(15)
            st.write(df_volume[['종목명', '현재가', '등락률', '거래대금(억)']].to_html(escape=False, index=False), unsafe_allow_html=True)

        with col2:
            st.subheader("💎 거래대금 상위 (금액 기준)")
            st.caption("실제 현금이 가장 많이 몰린 '진짜' 주인공들입니다.")
            # 거래대금 순서대로 상위 15개
            df_amount = all_data.sort_values(by='거래대금(억)', ascending=False).head(15)
            st.write(df_amount[['종목명', '현재가', '등락률', '거래대금(억)']].to_html(escape=False, index=False), unsafe_allow_html=True)

st.divider()
st.info("💡 왼쪽 리스트에는 '에스케이증권' 같은 저가주가, 오른쪽에는 시총이 큰 '삼성전자'나 '하이닉스' 등이 주로 포착될 거예요.")