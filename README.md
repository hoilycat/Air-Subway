🚇 Air-Subway: 실시간 대기 질 기반 지하철 혼잡도 예측
"보이지 않는 공기를 디자인하고, 데이터로 일상의 흐름을 예측하다"

Core Pipeline:

Data Ingestion: 공공데이터 API 및 SQL을 활용한 역사 내 환경 데이터(CO2, 미세먼지) 수집.

Analysis: Pandas/NumPy 기반의 시계열 상관관계 분석을 통한 데이터 정제.

Prediction: 과거 학습 데이터를 활용한 단기(10~30분) 혼잡도 예측 모델 구현.

Key Feature: Glanceable UI를 통한 즉각적 정보 전달 (Green/Yellow/Red 시각화).
