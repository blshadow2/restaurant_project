import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Union

def normalize_restaurant_name(name: str) -> str:
    """
    지점명 패턴을 제거하되, 매장명과 지점명 사이에 공백이 있을 때만 제거합니다.
    또한, 이름 뒤 괄호와 내용도 함께 제거합니다.
    """
    # 괄호 제거
    name = re.sub(r"\s*\([^)]*\)$", "", name)
    # ' 지점명' 제거
    return re.sub(r"\s+[가-힣]+점$", "", name)

def merge_site_data(
    data_nm: Dict[str, Any],
    data_ct: Dict[str, Any],
    data_km: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    미리 로드된 JSON 데이터(dict)를 normalize된 음식점명 기준으로 병합.
    - Naver의 address는 최상위에 저장
    - 리뷰 수 합산 -> 'total_reviews'
    - 평점 가중합 계산 후 평균 -> 'average_rating'
      * CatchTable의 경우, 개별 comment 내 별점(문자열)을 모두 추출하여 계산
      * 다른 소스는 기존 방식 유지
    - 원본 데이터는 소스별 리스트로 보관
    """
    merged: Dict[str, Dict[str, Any]] = {}

    for source_name, dataset in [
        ("naver", data_nm),
        ("catchtable", data_ct),
        ("kakaomap", data_km),
    ]:
        for raw_name, info in dataset.items():
            base_name = normalize_restaurant_name(raw_name)
            entry = merged.setdefault(base_name, {
                "total_reviews": 0,
                "rating_sum": 0.0,
                "rated_count": 0
            })

            # Naver 주소 저장
            if source_name == "naver" and info.get("address"):
                entry["address"] = info["address"]

            # 원본 데이터 보관
            entry.setdefault(source_name, []).append({
                "original_name": raw_name,
                "data": info
            })

            # 리뷰 수 합산
            rev_cnt = info.get("review_count") or info.get("review_cnt") or info.get("count") or 0
            try:
                rev_cnt = int(rev_cnt)
            except (ValueError, TypeError):
                rev_cnt = 0
            entry["total_reviews"] += rev_cnt

            # 평점 가중합 계산
            if source_name == "catchtable":
                # CatchTable의 경우, 개별 comment 내 별점을 모두 합산하여 rated_count로 사용
                comment_list = info.get("comment")
                if isinstance(comment_list, list):
                    # comment_list 예시: [["5.0", "텍스트..."], ["4.7", "텍스트..."], …]
                    for c in comment_list:
                        try:
                            # 첫 번째 요소가 별점 문자열인 경우에만 계산
                            rating_val = float(c[0])
                        except (ValueError, TypeError, IndexError):
                            continue
                        entry["rating_sum"] += rating_val
                        entry["rated_count"] += 1
                else:
                    # 만약 comment 리스트가 없거나 형식이 다를 때, 기존 로직 fallback
                    rating_raw = info.get("rating") or info.get("average_rating")
                    try:
                        rating = float(rating_raw) if rating_raw is not None else None
                    except (ValueError, TypeError):
                        rating = None
                    if rating is not None:
                        if rev_cnt > 0:
                            entry["rating_sum"] += rating * rev_cnt
                            entry["rated_count"] += rev_cnt
                        else:
                            entry["rating_sum"] += rating
                            entry["rated_count"] += 1
            else:
                # Naver, KakaoMap의 경우 기존 로직 유지
                rating_raw = info.get("rating") or info.get("average_rating")
                try:
                    rating = float(rating_raw) if rating_raw is not None else None
                except (ValueError, TypeError):
                    rating = None
                if rating is not None:
                    if rev_cnt > 0:
                        entry["rating_sum"] += rating * rev_cnt
                        entry["rated_count"] += rev_cnt
                    else:
                        entry["rating_sum"] += rating
                        entry["rated_count"] += 1

    # 평균 평점 계산 및 내부 키 정리
    for entry in merged.values():
        rated = entry.get("rated_count", 0)
        if rated > 0:
            entry["average_rating"] = round(entry["rating_sum"] / rated, 2)
        else:
            entry["average_rating"] = 0.0
        # 내부 계산용 키 삭제
        entry.pop("rating_sum", None)
        entry.pop("rated_count", None)

    return merged

def load_and_merge_json(
    nm_path: Union[str, Path],
    ct_path: Union[str, Path],
    km_path: Union[str, Path]
) -> Dict[str, Dict[str, Any]]:
    """
    파일 경로를 받아 JSON을 로드하고 merge_site_data로 병합한 결과를 반환합니다.
    """
    with open(nm_path, encoding="utf-8") as f:
        data_nm = json.load(f)
    with open(ct_path, encoding="utf-8") as f:
        data_ct = json.load(f)
    with open(km_path, encoding="utf-8") as f:
        data_km = json.load(f)

    return merge_site_data(data_nm, data_ct, data_km)

# 모듈로 사용 시 편리하게 호출
if __name__ == "__main__":
    base_dir = Path(__file__).parent
    merged = load_and_merge_json(
        base_dir / "reviews_NM.json",
        base_dir / "reviews_ct.json",
        base_dir / "reviews_KM.json"
    )
    # 결과를 즉시 사용하거나 파일로 저장 가능
    print(f"Merged {len(merged)} restaurants.")
    with open(base_dir / "merged_restaurants.json", "w", encoding="utf-8") as fout:
        json.dump(merged, fout, ensure_ascii=False, indent=2)
