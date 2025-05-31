import os
import json
import re
import math
import requests
from pathlib import Path
from merging_restaurant import load_and_merge_json
from config import top_CATEGORIES as TOP_CATEGORIES, subcategory_ALIASES as SUBCATEGORY_ALIASES, subcategory_WEIGHTS as DEFAULT_WEIGHTS, prefs, current_address
from typing import Tuple, Optional

# 작업 디렉터리를 스크립트 위치로 변경
os.chdir(os.path.dirname(os.path.abspath(__file__)))

WEIGHTS_FILE = 'user_weights.json'

def load_weights():
    if os.path.exists(WEIGHTS_FILE):
        try:
            with open(WEIGHTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return DEFAULT_WEIGHTS.copy()

def save_weights(weights):
    with open(WEIGHTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(weights, f, ensure_ascii=False, indent=2)

# 동적 하위 카테고리 가중치
SUBCATEGORY_WEIGHTS = load_weights()

# Kakao API Key 환경변수
KAKAO_API_KEY = 'af2b9e3f7feb89b376a43ec648ae815e'

# 지오코딩 함수
def geocode_kakao(address: str) -> Optional[Tuple[float, float]]:
    if not KAKAO_API_KEY:
        return None
    url = 'https://dapi.kakao.com/v2/local/search/address.json'
    headers = {'Authorization': f'KakaoAK {KAKAO_API_KEY}'}
    params = {'query': address}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        return None
    docs = resp.json().get('documents') or []
    if not docs:
        return None
    x = float(docs[0]['x']); y = float(docs[0]['y'])
    return (y, x)

# Haversine
def haversine(c1: Tuple[float, float], c2: Tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, c1)
    lat2, lon2 = map(math.radians, c2)
    dlat = lat2 - lat1; dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * 6371000 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# 데이터 로드
def load_merged_data(data):
    restaurants = []
    for name, info in data.items():
        rest = {
            'name': name,
            'total_reviews': info.get('total_reviews', 0),
            'rating': info.get('average_rating', 0.0),
            'address': info.get('address', None),
            'raw_categories': []
        }
        raw_set = set()
        for lst in info.values():
            if isinstance(lst, list):
                for item in lst:
                    cat = item.get('data', {}).get('category', '') or ''
                    raw_set.update([p.strip() for p in cat.split(',') if p.strip()])
        rest['raw_categories'] = sorted(raw_set)
        # top_category
        tc = '기타'
        for detail in rest['raw_categories']:
            part = detail.lower()
            for cat, kws in TOP_CATEGORIES.items():
                if any(kw in part for kw in kws): tc = cat; break
            if tc != '기타': break
        rest['top_category'] = tc
        restaurants.append(rest)
    return restaurants

# 가중치 점수
def compute_weighted_score(r):
    factor = 1.0
    for raw in r['raw_categories']:
        key = SUBCATEGORY_ALIASES.get(raw.lower(), raw.lower())
        factor += SUBCATEGORY_WEIGHTS.get(key, 0)
    factor += (prefs.get(r['top_category'], 0) - 3) * 0.2
    return r['total_reviews'] * factor

# 거리순 정렬
def sort_by_distance(restaurants, user_coord):
    entries = []
    for r in restaurants:
        addr = r.get('address')
        if not addr: continue
        coord = geocode_kakao(addr)
        if not coord: continue
        dist = haversine(user_coord, coord)
        rr = r.copy(); rr['distance_m'] = dist
        entries.append(rr)
    return sorted(entries, key=lambda x: x['distance_m'])

# 방문 가중치 업데이트
def increase_weights(r, delta=0.1):
    updated = False
    for raw in r['raw_categories']:
        key = SUBCATEGORY_ALIASES.get(raw.lower(), raw.lower())
        SUBCATEGORY_WEIGHTS[key] = SUBCATEGORY_WEIGHTS.get(key, 0) + delta
        updated = True
    if updated:
        save_weights(SUBCATEGORY_WEIGHTS)
        print('✅ 가중치가 파일에 저장되었습니다.')

# 추천 함수
def recommend_by_review_count(restaurants, top_n=10):
    for r in restaurants: r['weighted_score'] = compute_weighted_score(r)
    lst = sorted(restaurants, key=lambda x: x['weighted_score'], reverse=True)
    print(f"\n🏆 리뷰 순 추천 (가중치) 상위 {top_n}개")
    for i, r in enumerate(lst[:top_n],1): print(f"{i}. {r['name']} ({r['total_reviews']}) - ⭐{r['rating']} [{r['top_category']}] {r.get('address')} (점수:{r['weighted_score']:.1f})")
    sel = int(input(f"\n번호 선택 (1-{top_n},0:건너뜀): ") or 0)
    if sel>0: increase_weights(lst[sel-1])

def recommend_by_top_category(restaurants, top_n=5):
    cats=list(TOP_CATEGORIES.keys())
    print('\n📂 상위 카테고리')
    for i,cat in enumerate(cats,1): print(f"{i}. {cat}")
    sel=int(input(f"\n번호 선택(1-{len(cats)}): ") or 0)
    if sel<1 or sel>len(cats): return
    chosen=cats[sel-1]
    subset=[r for r in restaurants if r['top_category']==chosen]
    for r in subset: r['weighted_score']=compute_weighted_score(r)
    lst=sorted(subset, key=lambda x: x['weighted_score'], reverse=True)
    print(f"\n🍽️ '{chosen}' 추천 상위 {top_n}개")
    for i,r in enumerate(lst[:top_n],1): print(f"{i}. {r['name']} ({r['total_reviews']}) - ⭐{r['rating']} {r.get('address')} (점수:{r['weighted_score']:.1f})")
    sel2=int(input(f"\n번호 선택(1-{top_n},0:건너뜀): ") or 0)
    if sel2>0: increase_weights(lst[sel2-1])

# 거리순 추천
def recommend_by_distance(restaurants):
    user_addr=current_address
    user_coord=geocode_kakao(user_addr)
    if not user_coord: print('주소 변환 실패'); return
    lst=sort_by_distance(restaurants, user_coord)
    print('\n📍 거리순 추천 목록')
    for i,r in enumerate(lst,1): print(f"{i}. {r['name']} - {r.get('address')} ({r['distance_m']:.1f}m)")

# 통계
def show_statistics(restaurants):
    total=len(restaurants)
    avg=sum(r['rating'] for r in restaurants if r['rating']>0)/max(len([r for r in restaurants if r['rating']>0]),1)
    totrev=sum(r['total_reviews'] for r in restaurants)
    print(f"\n📊 총:{total}, 평균평점:{avg:.2f}, 리뷰합:{totrev}")

# 메인
def main():
    data=load_and_merge_json('reviews_NM.json','reviews_ct.json','reviews_KM.json')
    restaurants=load_merged_data(data)
    print(f"✅ {len(restaurants)}개 로드 완료!")
    while True:
        print("\n1. 리뷰순 | 2. 카테고리별 | 3. 거리순 | 4. 통계 | 5. 종료")
        cmd=input('선택> ').strip()
        if cmd=='1': recommend_by_review_count(restaurants,int(input('몇개?') or 10))
        elif cmd=='2': recommend_by_top_category(restaurants,int(input('몇개?') or 5))
        elif cmd=='3': recommend_by_distance(restaurants)
        elif cmd=='4': show_statistics(restaurants)
        elif cmd=='5': break
        else: print('❌ 1-5 중 입력')

if __name__=='__main__': main()
