import os
import json
import math
import requests
from pathlib import Path
from merging_restaurant import load_and_merge_json

# 수정된 config.py에서 하위 카테고리 가중치만 불러옵니다.
from config import (
    top_CATEGORIES as TOP_CATEGORIES,
    subcategory_ALIASES,
    subcategory_WEIGHTS,   # HTML 인터페이스로 업데이트된 가중치가 반영되어 있다고 가정
    prefs,
    current_address,
    KAKAO_API_KEY,
)
from typing import Tuple, Optional

# 작업 디렉터리를 스크립트 위치로 변경
os.chdir(os.path.dirname(os.path.abspath(__file__)))

MERGED_WITH_GEOCODE = Path('merged_with_geocode.json')


def geocode_kakao(address: str) -> Optional[Tuple[float, float]]:
    """
    카카오 REST API를 이용하여 주소를 지오코딩.
    성공 시 (위도, 경도) 튜플을 반환하고, 실패 시 None.
    """
    if not address or not KAKAO_API_KEY:
        return None

    url = 'https://dapi.kakao.com/v2/local/search/address.json'
    headers = {'Authorization': f'KakaoAK {KAKAO_API_KEY}'}
    params = {'query': address}
    resp = requests.get(url, headers=headers, params=params)

    if resp.status_code != 200:
        return None

    docs = resp.json().get('documents', [])
    if not docs:
        return None

    x = float(docs[0]['x'])  # 경도
    y = float(docs[0]['y'])  # 위도
    return (y, x)


def haversine(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    두 위경도 좌표(coord1, coord2)를 입력받아, 지구 반지름(6371km)을 이용하여
    두 지점 간의 거리를 미터 단위로 계산해 반환.
    """
    lat1, lon1 = map(math.radians, coord1)
    lat2, lon2 = map(math.radians, coord2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371000 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_merged_data(data: dict) -> list:
    """
    load_and_merge_json으로 얻은 'data' 딕셔너리를 순회하며,
    필요한 필드(name, total_reviews, rating, address, latitude, longitude, raw_categories, top_category 등)를
    정리해 리스트 형태로 반환.
    """
    restaurants = []
    for name, info in data.items():
        rest = {
            'name': name,
            'total_reviews': info.get('total_reviews', 0),
            'rating': info.get('average_rating', 0.0),
            'address': info.get('address', None),
            'latitude': info.get('latitude', None),
            'longitude': info.get('longitude', None),
            'raw_categories': [],
        }

        # raw_categories 수집
        raw_set = set()
        for v in info.values():
            if isinstance(v, list):
                for item in v:
                    cat = item.get('data', {}).get('category', '') or ''
                    for x in [p.strip() for p in cat.split(',') if p.strip()]:
                        raw_set.add(x)
        rest['raw_categories'] = sorted(raw_set)

        # top_category 결정
        tc = '기타'
        for detail in rest['raw_categories']:
            part = detail.lower()
            for cat, keywords in TOP_CATEGORIES.items():
                if any(kw in part for kw in keywords):
                    tc = cat
                    break
            if tc != '기타':
                break
        rest['top_category'] = tc

        restaurants.append(rest)

    return restaurants


def compute_weighted_score(r: dict) -> float:
    """
    카테고리별 서브카테고리 가중치(subcategory_WEIGHTS)와 사용자 선호도를 이용해
    'total_reviews'와 곱한 최종 점수를 계산.
    """
    factor = 1.0
    for raw in r['raw_categories']:
        key = subcategory_ALIASES.get(raw.lower(), raw.lower())
        factor += subcategory_WEIGHTS.get(key, 0)
    factor += (prefs.get(r['top_category'], 0) - 3) * 0.2
    return r['total_reviews'] * factor


def sort_by_distance(restaurants: list, user_coord: Tuple[float, float]) -> list:
    """
    저장된 위·경도(lat, lng)를 이용해 사용자 좌표(user_coord)와의 거리를 계산,
    거리를 'distance_m' 키로 추가한 뒤 오름차순 정렬하여 반환.
    """
    entries = []
    for r in restaurants:
        lat = r.get('latitude')
        lng = r.get('longitude')
        if lat is None or lng is None:
            continue

        coord = (lat, lng)
        dist = haversine(user_coord, coord)
        rr = r.copy()
        rr['distance_m'] = dist
        entries.append(rr)

    return sorted(entries, key=lambda x: x['distance_m'])


def recommend_by_review_count(restaurants: list, top_n: int = 10) -> list:
    """
    리뷰 개수 순으로 상위(top_n) 음식점을 출력하고, 해당 리스트를 반환.
    """
    lst = sorted(restaurants, key=lambda x: x['total_reviews'], reverse=True)[:top_n]
    print('\n⭐ 리뷰 많은 순 추천 목록')
    for i, r in enumerate(lst, 1):
        print(f"{i}. {r['name']} - 리뷰 {r['total_reviews']}개, 평점 {r['rating']:.1f}")
    return lst


def recommend_by_category_choice(restaurants: list, top_n: int = 5) -> list:
    """
    사용자가 카테고리를 선택하도록 한 뒤, 해당 카테고리 내에서
    하위 카테고리 가중치 기반 상위(top_n) 음식점을 출력하고 리스트 반환.
    """
    # 1) 사용 가능한 top_category 목록 출력
    categories = list(TOP_CATEGORIES.keys())
    print("\n🔍 선택 가능한 카테고리:")
    for idx, cat in enumerate(categories, 1):
        print(f"{idx}. {cat}")
    choice = input("원하는 카테고리 번호를 입력하세요 (취소하려면 엔터): ").strip()
    if not choice.isdigit():
        print("카테고리 선택이 취소되었습니다.\n")
        return []
    idx = int(choice) - 1
    if idx < 0 or idx >= len(categories):
        print("잘못된 카테고리 번호입니다.\n")
        return []

    selected_cat = categories[idx]
    # 2) 해당 top_category에 속하는 음식점 필터링
    filtered = [r for r in restaurants if r['top_category'] == selected_cat]
    if not filtered:
        print(f"'{selected_cat}' 카테고리에 해당하는 음식점이 없습니다.\n")
        return []

    # 3) 가중치 기반 점수를 계산하여 상위 top_n 추출
    scored = [(r, compute_weighted_score(r)) for r in filtered]
    scored.sort(key=lambda x: x[1], reverse=True)
    lst = [r for r, _ in scored[:top_n]]

    # 결과 출력
    print(f"\n🎯 '{selected_cat}' 카테고리 가중치 기반 추천 목록")
    for i, r in enumerate(lst, 1):
        score = compute_weighted_score(r)
        print(f"{i}. {r['name']} - 점수 {score:.1f}, 평점 {r['rating']:.1f}")
    return lst


def recommend_by_distance(restaurants: list) -> list:
    """
    현재 설정된 current_address를 geocode_kakao로 변환하여 사용자 좌표를 얻고,
    저장된 위·경도를 기준으로 거리순으로 출력 및 리스트 반환.
    """
    user_coord = geocode_kakao(current_address)
    if not user_coord:
        print('주소 변환 실패')
        return []

    lst = sort_by_distance(restaurants, user_coord)
    print('\n📍 거리순 추천 목록')
    for i, r in enumerate(lst, 1):
        addr = r.get('address') or '주소 정보 없음'
        print(f"{i}. {r['name']} - {addr} ({r['distance_m']:.1f} m)")
    return lst


def show_statistics(restaurants: list):
    """
    전체 음식점 통계(개수, 평균 평점, 리뷰 합계) 출력.
    """
    total = len(restaurants)
    rated = [r for r in restaurants if r['rating'] > 0]
    avg = sum(r['rating'] for r in rated) / max(len(rated), 1)
    totrev = sum(r['total_reviews'] for r in restaurants)
    print(f"\n📊 총:{total}개, 평균평점:{avg:.2f}, 리뷰합:{totrev}")


def prompt_and_update_weights(_):
    """
    HTML 인터페이스를 통해 가중치를 직접 수정하기 때문에,
    이 함수는 더 이상 아무 작업도 하지 않습니다.
    """
    return


def main():
    """
    1) merged_with_geocode.json 파일이 존재하면 그 파일을 로드
    2) 없으면 load_and_merge_json으로 병합 후, 위·경도가 없는 레코드에 대해 지오코딩 수행
       → 'latitude', 'longitude' 필드를 data에 추가 → merged_with_geocode.json으로 저장
    3) load_merged_data를 호출해 restaurants 리스트 생성
    4) 사용자 입력 루프를 통해 추천 기능 실행 (가중치 수정은 HTML에서 처리)
    """
    if MERGED_WITH_GEOCODE.exists():
        # 이미 지오코드가 포함된 병합 결과가 있으면 그대로 불러오기
        with open(MERGED_WITH_GEOCODE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ '{MERGED_WITH_GEOCODE.name}'에서 위경도 데이터를 로드했습니다.")
    else:
        # 1) 세 개의 JSON 파일 병합
        data = load_and_merge_json('reviews_NM.json', 'reviews_ct.json', 'reviews_KM.json')

        # 2) 위경도 값이 없는 음식점에 한해 지오코딩 수행하여 data에 저장
        for name, info in data.items():
            # 이미 latitude/longitude가 있으면 건너뛰기
            if 'latitude' in info and 'longitude' in info \
               and info['latitude'] is not None and info['longitude'] is not None:
                continue

            addr = info.get('address', '').strip()
            if not addr:
                info['latitude'] = None
                info['longitude'] = None
                continue

            coord = geocode_kakao(addr)
            if coord:
                lat, lng = coord
                info['latitude'] = lat
                info['longitude'] = lng
            else:
                info['latitude'] = None
                info['longitude'] = None

            # API 호출 제한을 피하기 위해 약간의 대기
            import time
            time.sleep(0.2)

        # 3) 위경도 데이터를 포함한 병합 결과를 파일로 저장
        with open(MERGED_WITH_GEOCODE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 지오코드가 포함된 병합 데이터를 저장했습니다 → '{MERGED_WITH_GEOCODE.name}'")

    # 4) load_merged_data를 통해 restaurants 리스트 생성
    restaurants = load_merged_data(data)
    print(f"✅ {len(restaurants)}개 로드 완료!")

    # 5) 사용자 입력 루프
    while True:
        print("\n1. 리뷰순 | 2. 카테고리별 | 3. 거리순 | 4. 통계 | 5. 종료")
        cmd = input('선택> ').strip()
        if cmd == '1':
            n = input('몇개? ').strip()
            top_n = int(n) if n.isdigit() else 10
            rec_list = recommend_by_review_count(restaurants, top_n)
            # HTML에서 가중치를 업데이트하므로, 여기서는 아무 동작 없음
            prompt_and_update_weights(rec_list)

        elif cmd == '2':
            n = input('몇개? ').strip()
            top_n = int(n) if n.isdigit() else 5
            rec_list = recommend_by_category_choice(restaurants, top_n)
            prompt_and_update_weights(rec_list)

        elif cmd == '3':
            rec_list = recommend_by_distance(restaurants)
            prompt_and_update_weights(rec_list)

        elif cmd == '4':
            show_statistics(restaurants)

        elif cmd == '5':
            break

        else:
            print('❌ 1-5 중 입력')

if __name__ == '__main__':
    main()