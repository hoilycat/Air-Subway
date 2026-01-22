import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ==========================================
# 1. 족보 (매핑 테이블)
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

# ==========================================
# 2. 데이터 로드 (CSV)
# ==========================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("data/congestion_data.csv", encoding="utf-8")
        return df
    except:
        return pd.read_csv("data/congestion_data.csv", encoding="cp949")

# ⭐ 데이터 미리 로딩 (app.py에서 logic.df_congestion으로 씀)
df_congestion = load_data()

# ==========================================
# 3. 핵심 기능 (계산 로직들)
# ==========================================

# (1) 혼잡도 계산
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

# (2) 도착 정보 (API)
def get_arrival(station):
    clean_station = station.replace("역", "")
    try:
        # 학교 컴퓨터 secrets.toml 확인 필수!
        KEY_SUBWAY = st.secrets["seoul"]["subway_key"]
        url = f"http://swopenapi.seoul.go.kr/api/subway/{KEY_SUBWAY}/json/realtimeStationArrival/0/5/{clean_station}"
        response = requests.get(url)
        data = response.json()
        if "realtimeArrivalList" in data:
            return pd.DataFrame(data["realtimeArrivalList"])[["trainLineNm", "arvlMsg2", "recptnDt"]]
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# (3) 미세먼지 (API + 족보 적용)
def get_gu_air_quality(station):
    try:
        KEY_GENERAL = st.secrets["seoul"]["general_key"]
        url = f"http://openapi.seoul.go.kr:8088/{KEY_GENERAL}/json/RealtimeCityAir/1/25/"
        response = requests.get(url)
        data = response.json()
        
        if "RealtimeCityAir" in data:
            df = pd.DataFrame(data["RealtimeCityAir"]["row"])
            
            clean_station = station.replace("역", "")
            target_gu = STATION_TO_GU.get(clean_station, clean_station)
            
            result = df[df['MSRSTN_NM'].str.contains(target_gu)]
            if result.empty and "구" not in target_gu:
                 result = df[df['MSRSTN_NM'].str.contains(target_gu)]
            
            if not result.empty:
                return result.rename(columns={
                    "MSRSTN_NM": "지역", "PM": "미세먼지", "FPM": "초미세먼지", "CAI_GRD": "상태"
                })[["지역", "미세먼지", "초미세먼지", "상태"]]
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# (4) 날씨 (겨울철 Mock Data)
def get_weather_info(station):
    # API 복구 전까지 고정값 사용
    return -5.2, 35.0

# (5) 불쾌지수 계산기
def calculate_discomfort_index(temp, humi):
    if temp is None or humi is None:
        return 0, "정보 없음"
    di = 0.81 * temp + 0.01 * humi * (0.99 * temp - 14.3) + 46.3
    
    if di >= 80: return di, "매우 나쁨 (전원 불쾌) 🤬"
    elif di >= 75: return di, "나쁨 (50% 불쾌) 😠"
    elif di >= 68: return di, "보통 (10% 불쾌) 😐"
    else: return di, "좋음 (쾌적) 😊"