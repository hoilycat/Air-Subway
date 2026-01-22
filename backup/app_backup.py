import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ==========================================
# 1. 기본 설정 및 데이터 로드
# ==========================================
st.set_page_config(page_title="Air-Subway", page_icon="🚇", layout="centered")

st.title("🚇 Air-Subway")
st.caption("서울 지하철 혼잡도 기반 정밀 건강 진단 솔루션")

# 비밀 금고에서 키 가져오기
try:
    KEY_GENERAL = st.secrets["seoul"]["general_key"]
    KEY_SUBWAY = st.secrets["seoul"]["subway_key"]
except:
    st.error("🚨 비밀 금고(secrets.toml) 확인이 필요해요!")
    st.stop()

# CSV 데이터 로드 (캐싱)
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("data/congestion_data.csv", encoding="utf-8")
        return df
    except:
        return pd.read_csv("data/congestion_data.csv", encoding="cp949")

df_congestion = load_data()

# ==========================================
# 2. 데이터 수집 기능 (3종 세트)
# ==========================================

# (1) 혼잡도 (CSV 통계)
def get_real_congestion(station_name):
    now = datetime.now()
    weekday = now.weekday()
    day_type = "평일" if weekday <= 4 else ("토요일" if weekday == 5 else "일요일")
    
    hour = now.hour
    minute = now.minute
    time_col = f"{hour}시00분" if minute < 30 else f"{hour}시30분"
    
    if time_col not in df_congestion.columns:
        return 0, f"{day_type} {time_col} (운행종료)"

    clean_name = station_name.replace("역", "")
    condition = (df_congestion['출발역'] == clean_name) & (df_congestion['요일구분'] == day_type)
    rows = df_congestion[condition]
    
    if rows.empty:
        return -1, "데이터 없음"
    
    return rows[time_col].max(), f"{day_type} {time_col} 기준"

# (2) 실시간 도착 (API - VIP Key)
def get_arrival(station):
    clean_station = station.replace("역", "")
    url = f"http://swopenapi.seoul.go.kr/api/subway/{KEY_SUBWAY}/json/realtimeStationArrival/0/5/{clean_station}"
    try:
        response = requests.get(url)
        data = response.json()
        if "realtimeArrivalList" in data:
            return pd.DataFrame(data["realtimeArrivalList"])[["trainLineNm", "arvlMsg2", "recptnDt"]]
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# ==========================================
# 🗺️ 족보: 역 이름 -> 구(Gu) 이름 매핑
# (컴퓨터가 '종각'이 '종로구'인 걸 모르니까 알려주는 지도!)
# ==========================================
STATION_TO_GU = {
    "강남": "강남구", "역삼": "강남구", "삼성": "강남구", "신사": "강남구", "압구정": "강남구", "청담": "강남구",
    "종각": "종로구", "종로3가": "종로구", "종로5가": "종로구", "혜화": "종로구", "광화문": "종로구",
    "시청": "중구", "서울역": "중구", "을지로": "중구", "명동": "중구", "충무로": "중구", "동대문": "중구",
    "홍대입구": "마포구", "합정": "마포구", "신촌": "서대문구", "이대": "서대문구",
    "여의도": "영등포구", "영등포": "영등포구", "당산": "영등포구",
    "잠실": "송파구", "가락시장": "송파구", "잠실나루": "송파구",
    "건대입구": "광진구", "성수": "성동구", "왕십리": "성동구",
    "고속터미널": "서초구", "교대": "서초구", "서초": "서초구", "양재": "서초구",
    "사당": "동작구", "노량진": "동작구", "이수": "동작구",
    "구로디지털단지": "구로구", "신도림": "구로구",
    "용산": "용산구", "이태원": "용산구", "한남": "용산구"
}

# (3) 외부 미세먼지 (이름표 버그 수정 완료!)
def get_gu_air_quality(station):
    try:
        KEY_GENERAL = st.secrets["seoul"]["general_key"]
    except:
        return pd.DataFrame()

    url = f"http://openapi.seoul.go.kr:8088/{KEY_GENERAL}/json/RealtimeCityAir/1/25/"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if "RealtimeCityAir" in data:
            df = pd.DataFrame(data["RealtimeCityAir"]["row"])
            
            # 1. 족보 확인 (역 -> 구)
            clean_station = station.replace("역", "")
            target_gu = STATION_TO_GU.get(clean_station, clean_station)
            
            # 2. 검색 (여기서 'MSRSTN_NM'으로 찾아야 함! 👈 여기가 핵심!)
            # 'MSRSTN_NM'이 '구 이름'이야.
            result = df[df['MSRSTN_NM'].str.contains(target_gu)]
            
            # 만약 없으면 '구'를 떼거나 붙여서 재시도
            if result.empty and "구" not in target_gu:
                 result = df[df['MSRSTN_NM'].str.contains(target_gu)]
            
            if not result.empty:
                # 3. 이름표 예쁘게 바꿔서 내보내기
                return result.rename(columns={
                    "MSRSTN_NM": "지역", 
                    "PM": "미세먼지",      # API가 PM이라고 줌
                    "FPM": "초미세먼지",    # API가 FPM이라고 줌
                    "CAI_GRD": "상태"      # API가 CAI_GRD라고 줌
                })[["지역", "미세먼지", "초미세먼지", "상태"]]
                
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# (4) 날씨 및 불쾌지수 (API - RealtimeWeatherStation 사용!) 🌟 New!
def get_weather_info(station):
    """
    S-DoT 대신 더 안정적인 '서울시 기상관측소(SAWS)' 데이터를 사용합니다.
    """
    clean_station = station.replace("역", "").replace("구", "") # "강남"으로 검색
    
    # 🌟 RealtimeWeatherStation 서비스 사용
    url = f"http://openapi.seoul.go.kr:8088/{KEY_GENERAL}/json/RealtimeWeatherStation/1/5/{clean_station}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if "RealtimeWeatherStation" in data and "row" in data["RealtimeWeatherStation"]:
            row = data["RealtimeWeatherStation"]["row"][0]
            # SAWS_TA_AVG (기온), SAWS_HD (습도)
            temp = float(row.get("SAWS_TA_AVG", 0))
            humi = float(row.get("SAWS_HD", 0))
            return temp, humi
        else:
            return None, None
    except:
        return None, None

def calculate_discomfort_index(temp, humi):
    if temp is None or humi is None:
        return 0, "정보 없음"
    # 불쾌지수 공식
    di = 0.81 * temp + 0.01 * humi * (0.99 * temp - 14.3) + 46.3
    
    status = "쾌적 😊"
    if di >= 80: status = "매우 나쁨 (전원 불쾌) 🤬"
    elif di >= 75: status = "나쁨 (50% 불쾌) 😠"
    elif di >= 68: status = "보통 (10% 불쾌) 😐"
    
    return di, status

# ==========================================
# 🩺 핵심 기능: Dr. 설의 정밀 건강 리포트 (Ver. 2.0)
# ==========================================
def show_survival_report(congestion_score, ref_text, air_df, temp, humi):
    # 1. 환경 변수 계산
    di_score, di_status = calculate_discomfort_index(temp, humi)
    
    pm10_val = 0
    air_status = "보통"
    if not air_df.empty and 'PM10' in air_df.columns:
        pm10_val = float(air_df.iloc[0]['PM10'])
        if pm10_val >= 81: air_status = "나쁨"
        elif pm10_val <= 30: air_status = "좋음"

    st.markdown("### 🩺 Dr. 설의 정밀 건강 진단서")
    st.caption(f"📊 진단 근거: 서울교통공사 혼잡도 통계 ({ref_text})")

    # [섹션 1] 외부 환경 브리핑 (날씨)
    if temp is not None:
        st.info(f"🌡️ **외부 날씨:** 기온 {temp}℃ / 습도 {humi}% (불쾌지수: {di_status})")
    else:
        st.info("🌡️ 외부 날씨 정보를 가져올 수 없습니다. (하지만 실내 분석은 계속됩니다!)")

    # [섹션 2] 상세 진단 (2단 컬럼)
    col1, col2 = st.columns(2)

    # 🔴 위험 (혼잡도 55% 이상)
    if congestion_score >= 55:
        st.error(f"⛔ [종합 판정] 탑승 금지! (혼잡도 {congestion_score:.1f}%)")
        
        with col1:
            st.markdown("#### 🧠 정신 건강 (Mental)")
            st.metric("스트레스 호르몬", "코르티솔 급증 🔺", "전투 모드 돌입", delta_color="inverse")
            st.write("**진단:** 퍼스널 스페이스(45cm)가 붕괴되었습니다. 뇌가 현재 상황을 '위협'으로 인식하여 예민해져 있습니다.")
            if di_score >= 75:
                st.write(f"🥵 **날씨 영향:** 엎친 데 덮친 격! 높은 불쾌지수({di_score:.0f})로 인해 사소한 접촉도 큰 싸움이 될 수 있습니다.")
        
        with col2:
            st.markdown("#### 💪 신체 건강 (Physical)")
            st.metric("감염/피로 위험", "매우 높음 😷", "마스크 KF94 필수", delta_color="inverse")
            st.write("**진단:** 콩나물시루 효과로 인해 호흡량이 30% 감소합니다. 뇌 산소 공급 부족으로 하품이 계속 나올 것입니다.")
            if air_status == "나쁨":
                st.write(f"🌫️ **공기 영향:** 외부 미세먼지({pm10_val})까지 최악입니다. 절대 입을 벌리지 마세요.")

        st.warning("💊 **최종 처방:** 지금 타면 100% 후회합니다. 근처 카페에서 30분간 '멍 때리기'를 처방합니다.")

    # 🟡 주의 (혼잡도 35% ~ 54%)
    elif congestion_score >= 35:
        st.warning(f"⚠️ [종합 판정] 주의 요망 (혼잡도 {congestion_score:.1f}%)")
        
        with col1:
            st.markdown("#### 🧠 정신 건강 (Mental)")
            st.metric("집중력", "40% 감소 📉", "독서 불가", delta_color="inverse")
            st.write("**진단:** 웅성거림과 안내방송 소음으로 인해 깊은 사고가 불가능합니다. 가벼운 유튜브 시청만 가능합니다.")
            if di_score <= 68:
                st.write("✨ **날씨 영향:** 다행히 외부가 쾌적하여 환승 구간에서는 숨통이 트일 것입니다.")

        with col2:
            st.markdown("#### 💪 신체 건강 (Physical)")
            st.metric("근육 피로도", "누적 중 🔋", "어깨/허리 주의", delta_color="off")
            st.write("**진단:** 손잡이를 잡고 균형을 잡느라 코어 근육이 계속 긴장 상태입니다.")

        st.info("💊 **최종 처방:** 가장 끝 칸(1-1, 10-4)으로 이동하세요. 그곳엔 아직 산소가 남아있습니다.")

    # 🟢 쾌적 (혼잡도 34% 이하)
    else:
        st.success(f"✅ [종합 판정] 탑승 강력 추천 (혼잡도 {congestion_score:.1f}%)")
        
        with col1:
            st.markdown("#### 🧠 정신 건강 (Mental)")
            st.metric("창의력/학습능력", "최상 🧠", "도파민 안정", delta_color="normal")
            st.write("**진단:** 심리적 안정감이 확보되었습니다. 어려운 전공 서적이나 기획안을 구상하기에 최적의 시간입니다.")
        
        with col2:
            st.markdown("#### 💪 신체 건강 (Physical)")
            st.metric("에너지 보존율", "100% ⚡", "착석 가능성 높음", delta_color="normal")
            st.write("**진단:** 앉아서 갈 확률이 80% 이상입니다. 다리 부종을 예방하고 꿀잠을 잘 수 있습니다.")

        st.info("💊 **최종 처방:** 이 기차는 '움직이는 도서관'입니다. 당장 타세요!")

# ==========================================
# 📈 Plus Alpha: 시각화 & 골든타임 (버그 수정 Ver.)
# ==========================================
def show_congestion_chart(station_name):
    """
    무시무시한 표 대신, 깔끔한 '대시보드'로 보여줍니다.
    """
    now = datetime.now()
    weekday = now.weekday()
    day_type = "평일" if weekday <= 4 else ("토요일" if weekday == 5 else "일요일")
    
    clean_name = station_name.replace("역", "")
    
    # 1. 데이터 필터링 (역 이름 & 요일)
    condition = (df_congestion['출발역'] == clean_name) & (df_congestion['요일구분'] == day_type)
    rows = df_congestion[condition]
    
    if rows.empty:
        return

    # 2. 데이터 전처리 (시간대별 혼잡도 추출)
    # 🚨 수정된 부분: "시"와 "분"이 모두 들어간 컬럼만 가져오기! ('구분' 제외)
    time_cols = [c for c in df_congestion.columns if "시" in c and "분" in c]
    
    # 상행/하행 중 더 혼잡한 값 사용 (숫자만 확실하게 가져오기)
    chart_data = rows[time_cols].max()
    
    # -------------------------------------------------------
    # 🌟 1. 핵심 요약 카드 (가로로 배치!)
    # -------------------------------------------------------
    st.markdown("### 📊 한눈에 보는 혼잡도 브리핑")
    
    # 가장 혼잡한 시간 & 가장 널널한 시간 찾기
    worst_time = chart_data.idxmax()
    worst_val = chart_data.max()
    
    best_time = chart_data.idxmin()
    best_val = chart_data.min()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("😡 오늘의 최악", f"{worst_time}", f"{worst_val}% (혼잡)", delta_color="inverse")
    
    with col2:
        st.metric("😇 오늘의 천국", f"{best_time}", f"{best_val}% (여유)", delta_color="normal")
        
    with col3:
        # 현재 시간 이후 골든타임 계산
        current_hour = now.hour
        golden_time = "-"
        golden_val = 100
        
        for t_col in time_cols:
            try:
                # "18시30분" -> 18 (시간만 추출)
                t_hour = int(t_col.split("시")[0])
                if t_hour >= current_hour:
                    val = chart_data[t_col]
                    if val < golden_val:
                        golden_val = val
                        golden_time = t_col
            except:
                continue
                
        st.metric("🚀 추천 출발 시간", f"{golden_time}", f"{golden_val}% (최적)")

   # -------------------------------------------------------
    # 🌟 2. 그래프 (선 차트)
    # -------------------------------------------------------
    st.write("") 
    st.caption("🔻 시간대별 혼잡도 변화 그래프")
    st.line_chart(chart_data, color="#FF4B4B", height=250)

    # -------------------------------------------------------
    # 🌟 3. 상세 데이터 (표 예쁘게 만들기!)
    # -------------------------------------------------------
    with st.expander("🔢 상세 데이터 표 보기"):
        # Series를 DataFrame으로 변환하고, 인덱스를 컬럼으로 끄집어냄
        table_df = chart_data.reset_index()
        table_df.columns = ["시간", "혼잡도(%)"] # 이름표 붙이기!
        
        # 인덱스 번호(0, 1, 2...)는 숨기고 보여주기
        st.dataframe(table_df, use_container_width=True, hide_index=True)
        st.caption("※ 서울교통공사 통계 데이터 기반")


# ==========================================
# 4. 메인 실행 블록 (깔끔한 UI Ver.)
# ==========================================
station = st.text_input("어느 역이 궁금하세요?", "강남")

if st.button("분석 시작 🚀"):
    st.divider()

    # 1. [메인] 가장 중요한 '도착 정보'는 바로 보여주기
    st.subheader(f"🚄 {station}역 실시간 도착")
    st.dataframe(get_arrival(station), hide_index=True)

    # 2. [메인] Dr. 설의 진단서 & 차트 (여기가 핵심!)
    congestion, ref_time = get_real_congestion(station)
    air_df = get_gu_air_quality(station)
    
    # [임시] 겨울 날씨
    temp = -5.2
    humi = 35.0
    st.toast("날씨 서버 점검 중! 가상 데이터 사용", icon="❄️")

    # (1) 진단서 발행
    show_survival_report(congestion, ref_time, air_df, temp, humi)
    
    st.divider()
    
    # (2) 대시보드 차트 (방금 만든 거!)
    show_congestion_chart(station)

    # 3. [서브] 덜 중요한 날씨 표는 숨겨두기 (Click to open)
    st.write("---")
    with st.expander(f"🍃 {station} 주변 대기 정보 (상세 보기)"):
        if not air_df.empty:
            st.dataframe(air_df, hide_index=True)
        else:
            st.write("정보 없음")