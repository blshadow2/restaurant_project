#6. 사용자의 주소를 받고 특정 범위 내에 상위 5개의 식당을 찾아주는 프로그램을 만드시오.

# 1-사용자 위치 기반 추천 프로그램
from math import radians, sin, cos, sqrt, atan2  # 지구 위 두 지점 사이의 실제 거리를 계산할 때 쓰는 삼각함수들을 불러옵니다.
import pandas as pd  # 데이터 처리를 위해 pandas 라이브러리를 불러옵니다.
from geopy.geocoders import Nominatim  # 주소를 위도와 경도로 변환하기 위한 geopy 라이브러리의 Nominatim을 불러옵니다.
import time  # 시간 지연을 위해 time 모듈을 불러옵니다.

def haversine(lat1, lon1, lat2, lon2):  # 위도와 경도를 사용해 두 장소 간의 실제 직선 거리(km 단위)를 계산해주는 함수입니다.
    R = 6371  # 지구의 반지름을 킬로미터 단위로 설정합니다.
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])  # 위도와 경도를 라디안으로 변환합니다.
    dlat = lat2 - lat1  # 두 지점의 위도 차이를 계산합니다.
    dlon = lon2 - lon1  # 두 지점의 경도 차이를 계산합니다.
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2  # 두 지점 사이의 거리 계산을 위한 공식입니다.
    c = 2 * atan2(sqrt(a), sqrt(1 - a))  # 두 지점 사이의 각도를 계산합니다.
    return R * c  # 지구의 반지름과 각도를 곱해 실제 거리를 반환합니다.

# 사용자 주소 입력 및 좌표 변환
geo = Nominatim(user_agent="myapp")  # 사람이 입력한 주소를 위도/경도 좌표로 바꿔주는 도구입니다. 
user_address = input("현재 위치 주소를 입력하세요 (예: 서울특별시 영등포구 여의도동): ")  # 사용자에게 주소를 입력받습니다.
location = geo.geocode(user_address)  # 입력받은 주소를 위도와 경도로 변환합니다.
if not location:  # 주소를 찾지 못한 경우
    print("주소를 찾을 수 없습니다.")  # 오류 메시지를 출력합니다.
    exit()  # 프로그램을 종료합니다.
user_lat, user_lon = location.latitude, location.longitude  # 변환된 위도와 경도를 변수에 저장합니다.

# CSV 데이터 불러오기
try:
    df = pd.read_csv("/Users/ihyeonseong/Desktop/파이썬/DATAGO_YEONGDEUNGPO_2022.RSTR_INFO_ENG.csv")  # CSV(표 형태) 파일에서 식당 데이터를 불러옵니다.
except FileNotFoundError:  # 파일을 찾을 수 없는 경우
    print("CSV 파일을 찾을 수 없습니다. 경로를 확인하세요.")  # 오류 메시지를 출력합니다.
    exit()  # 프로그램을 종료합니다.
df = df.head(30)  # 상위 30개 행만 사용하여 데이터 크기를 줄입니다.

# 반경 3km 이내의 식당 필터링
print("\n반경 40km 이내 식당:")  # 사용자가 입력한 위치를 기준으로 가까운 식당을 찾기 위해 메시지를 출력합니다.
found = False  # 식당을 찾았는지를 나타내는 변수입니다.
results = []  # 결과를 저장할 리스트입니다.

for _, row in df.iterrows():  # 데이터프레임의 각 행을 반복합니다.
    address = row.get("도로명주소")  # 현재 행에서 도로명 주소를 가져옵니다.
    if pd.isna(address):  # 주소가 없는 경우
        continue  # 다음 행으로 넘어갑니다.
    try:
        location = geo.geocode(address)  # 주소를 위도와 경도로 변환합니다.
        time.sleep(1)  # API 호출 제한을 피하기 위해 1초 대기합니다.
    except:  # 예외가 발생할 경우
        continue  # 다음 행으로 넘어갑니다.
    if not location:  # 주소를 찾지 못한 경우
        continue  # 다음 행으로 넘어갑니다.
    lat = location.latitude  # 변환된 위도를 변수에 저장합니다.
    lon = location.longitude  # 변환된 경도를 변수에 저장합니다.
    
    distance = haversine(user_lat, user_lon, lat, lon)  # 사용자의 위치와 식당의 위치 간의 거리를 계산합니다.
   
    if distance <= 40:  # 거리가 40km 이하인 경우
        name = row.get("식당명", "Unknown")  # 식당 이름을 가져옵니다. 만약 이름이 없으면 'Unknown'으로 설정합니다.
        business_type = row.get("영업신고증업태명", "업태정보 없음")  # 업종 정보를 가져옵니다. 없으면 '업태정보 없음'으로 설정합니다.
        results.append((distance, name, business_type))  # 거리, 이름, 업종 정보를 하나의 묶음으로 리스트에 저장합니다.
        found = True  # 식당을 찾았음을 표시합니다.

results.sort()  # 거리 기준으로 정렬합니다.

if found:  # 식당을 찾은 경우
    for distance, name, business_type in results[:5]:  # 상위 5개 식당을 출력합니다.
        print(f"- {name} (거리: {distance:.2f}km, 업태: {business_type})")  # 식당 이름과 거리, 업종 정보를 출력합니다.
else:  # 식당을 찾지 못한 경우
    print("가까운 곳에는 없음")  # 오류 메시지를 출력합니다.