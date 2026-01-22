import streamlit as st
import pandas as pd
from datetime import datetime
import logic  # 👈 [중요] 방금 만든 logic.py를 불러옴!

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(
    page_title="Air-Subway",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. UI 그리기 함수 (화면 담당)
# ==========================================

# (1) Dr.설 리포트 화면
def show_survival_report(congestion_score, ref_text, air_df, temp, humi):
    # logic 파일에 있는 계산기 사용!
    di_score, di_status = logic.calculate_discomfort_index(temp, humi)
    
    pm10_val = 0
    air_status = "보통"
    if not air_df.empty and '미세먼지' in air_df.columns:
        pm10_val = float(air_df.iloc[0]['미세먼지'])
        if pm10_val >= 81: air_status = "나쁨"
        elif pm10_val <= 30: air_status = "좋음"

    st.markdown("### 🩺 Dr. 설의 정밀 건강 진단서")
    st.caption(f"📊 진단 근거: {ref_text}")
    st.info(f"🌡️ **외부 날씨:** 기온 {temp}℃ / 습도 {humi}% (불쾌지수: {di_status})")

    col1, col2 = st.columns(2)

    # 🔴 위험
    if congestion_score >= 55:
        st.error(f"⛔ [탑승 금지] 혼잡도 {congestion_score:.1f}%")
        with col1:
            st.markdown("#### 🧠 정신 건강")
            st.metric("스트레스", "심각 🤬", "전투 모드", delta_color="inverse")
            st.write("퍼스널 스페이스 붕괴! 예민함 폭발 직전입니다.")
        with col2:
            st.markdown("#### 💪 신체 건강")
            st.metric("감염 위험", "매우 높음 😷", "KF94 필수", delta_color="inverse")
            st.write("산소 부족으로 하품이 계속 나옵니다.")
        st.warning("💊 **처방:** 카페에서 30분 쉬었다 가세요.")

    # 🟡 주의
    elif congestion_score >= 35:
        st.warning(f"⚠️ [주의 요망] 혼잡도 {congestion_score:.1f}%")
        with col1:
            st.markdown("#### 🧠 정신 건강")
            st.metric("집중력", "저하 📉", delta_color="inverse")
            st.write("소음으로 인해 독서는 무리입니다.")
        with col2:
            st.markdown("#### 💪 신체 건강")
            st.metric("피로도", "누적 중 🔋", delta_color="off")
            st.write("손잡이를 잡느라 어깨가 결립니다.")
        st.info("💊 **처방:** 가장 끝 칸(1-1, 10-4)을 공략하세요.")

    # 🟢 쾌적
    else:
        st.success(f"✅ [탑승 추천] 혼잡도 {congestion_score:.1f}%")
        with col1:
            st.markdown("#### 🧠 정신 건강")
            st.metric("학습 능률", "최상 🧠", delta_color="normal")
            st.write("움직이는 도서관입니다. 공부하세요!")
        with col2:
            st.markdown("#### 💪 신체 건강")
            st.metric("착석 확률", "80% 이상 ⚡", delta_color="normal")
            st.write("앉아서 꿀잠 가능합니다.")
        st.info("💊 **처방:** 지금 당장 찍고 들어가세요!")

# (2) 대시보드 차트 화면
def show_congestion_chart(station_name):
    now = datetime.now()
    weekday = now.weekday()
    day_type = "평일" if weekday <= 4 else ("토요일" if weekday == 5 else "일요일")
    clean_name = station_name.replace("역", "")
    
    # 🌟 logic 파일의 데이터 사용!
    df = logic.df_congestion
    
    condition = (df['출발역'] == clean_name) & (df['요일구분'] == day_type)
    rows = df[condition]
    
    if rows.empty: return

    time_cols = [c for c in df.columns if "시" in c and "분" in c]
    chart_data = rows[time_cols].max()
    
    st.markdown("### 📊 한눈에 보는 혼잡도 브리핑")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("😡 오늘의 최악", f"{chart_data.idxmax()}", f"{chart_data.max()}%")
    with col2:
        st.metric("😇 오늘의 천국", f"{chart_data.idxmin()}", f"{chart_data.min()}%")
    with col3:
        # 🌟 3시간 제한 로직 적용됨!
        current_hour = now.hour
        limit_hour = current_hour + 3
        golden_time = "-"
        golden_val = 100
        for t_col in time_cols:
            try:
                t_hour = int(t_col.split("시")[0])
                if t_hour == 0: t_hour = 24
                if current_hour <= t_hour <= limit_hour:
                    val = chart_data[t_col]
                    if val < golden_val:
                        golden_val = val
                        golden_time = t_col
            except: continue
        st.metric("🚀 곧 출발한다면?", f"{golden_time}", f"{golden_val}% (추천)")

    st.write("")
    st.line_chart(chart_data, color="#FF4B4B", height=250)
    
    with st.expander("🔢 상세 데이터 표 보기"):
        table_df = chart_data.reset_index()
        table_df.columns = ["시간", "혼잡도(%)"]
        st.dataframe(table_df, use_container_width=True, hide_index=True)

# ==========================================
# 3. 메인 실행 (UI 배치)
# ==========================================
st.markdown("# 🚇💨 **Air-Subway**") 

with st.sidebar:
    st.header("🎛️ 컨트롤 패널")
    st.info("오늘의 출근길, 생존할 수 있을까?")
    station = st.text_input("어느 역이 궁금하세요?", "강남")
    run_btn = st.button("분석 시작 🚀", type="primary")
    st.divider()
    st.caption("Developed by 용용 & Dr.Seol")

if run_btn:
    # 🌟 logic 함수 호출!
    congestion, ref_time = logic.get_real_congestion(station)
    air_df = logic.get_gu_air_quality(station)
    arrival_df = logic.get_arrival(station)
    temp, humi = logic.get_weather_info(station)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader(f"🚄 {station}역 도착 정보")
        st.dataframe(arrival_df, hide_index=True)
    with col2:
        st.subheader(f"🍃 주변 대기 정보")
        if not air_df.empty:
            st.dataframe(air_df, hide_index=True)
        else:
            st.info("미세먼지 정보 없음")

    st.divider()
    show_survival_report(congestion, ref_time, air_df, temp, humi)
    st.divider()
    show_congestion_chart(station)

else:
    st.markdown("### 👋 환영합니다!")
    st.write("왼쪽 사이드바에서 역 이름을 입력하고 **[분석 시작]**을 눌러주세요.")