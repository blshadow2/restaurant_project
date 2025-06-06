def generate_result_html():
    import json
    import time
    import sys
    from pathlib import Path
    from sorting_restaurant import load_merged_data, recommend_by_distance, geocode_kakao, compute_weighted_score
    from merging_restaurant import load_and_merge_json
    from config import current_address

    MERGED_WITH_GEOCODE = Path("merged_with_geocode.json")
    TEMPLATE_PATH = Path(__file__).parent / "templates" / "result.html"
    # 2) 병합 + 지오코드 확보 로직을 html.py에 직접 구현
    if MERGED_WITH_GEOCODE.exists():
        with open(MERGED_WITH_GEOCODE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ '{MERGED_WITH_GEOCODE.name}'에서 위경도 데이터를 로드했습니다.")
    else:
        # 2-1) 세 개의 JSON 파일 병합
        data = load_and_merge_json("reviews_NM.json", "reviews_ct.json", "reviews_KM.json")

        # 2-2) 위·경도 값이 없는 음식점에 대해 지오코딩 수행
        for name, info in data.items():
            if info.get('latitude') is not None and info.get('longitude') is not None:
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

            time.sleep(0.2)  # API 호출 제한을 피하기 위해 대기

        # 2-3) 지오코드가 포함된 합친 데이터를 파일로 저장
        with open(MERGED_WITH_GEOCODE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 지오코드가 포함된 병합 데이터를 저장했습니다 → '{MERGED_WITH_GEOCODE.name}'")

    # 3) load_merged_data로 restaurants 리스트 생성
    restaurants = load_merged_data(data)
    print(f"✅ {len(restaurants)}개 로드 완료!")

    # 4) 사용자 좌표 얻기 및 거리순 정렬
    user_coord = geocode_kakao(current_address)
    if not user_coord:
        print("주소 변환 실패")
        restaurants = []
    else:
        # 거리순 정렬
        restaurants = recommend_by_distance(restaurants)

        # 2km 이내 음식점만 가중치 적용
        filtered = [r for r in restaurants if r.get("distance_m", 99999) <= 2000]

        # ⬇ 가중치 점수 계산 후 높은 순으로 재정렬
        restaurants_with_score = [
            (r, compute_weighted_score(r)) for r in filtered
        ]
        restaurants_with_score.sort(key=lambda x: x[1], reverse=True)
        restaurants = [r for r, _ in restaurants_with_score]

    # 4) HTML 파일 생성
    with open(TEMPLATE_PATH, "w", encoding="utf-8") as out:
        out.write("""<!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>식당 결과 페이지</title>
        <link rel="stylesheet" href="/static/results.css">
    </head>
    <body>
        <div class="main-frame">
            <div class="banner">
                <img src="/static/mascot.png" alt="logo" class="logo">
            </div>
    """)

        # 카테고리 버튼
        categories = ["한식", "양식", "일식", "중식", "아시이음식", "카페·베이커리", "주점", "기타"]
        for i, cat in enumerate(categories, start=1):
            out.write(f'''
            <button class="category category-{i}" data-category="{cat}" onclick="handleNavigation({i})" aria-label="네비게이션 버튼 {i}">
                <span class="category-text">{cat}</span>
            </button>
            ''')

        # 카드 컨테이너 시작
        out.write('<div class="divider-line-1"></div>\n')
        out.write('<div class="content-card-scroll" style="overflow-y: hidden;">\n')

        # 5) 거리순 정렬된 restaurants 리스트로 카드 생성
        for idx, info in enumerate(restaurants):
            name = info.get("name", f"음식점 {idx+1}")
            category = info.get("top_category", "")
            subcategory_list = info.get("raw_categories", [])
            subcategory = subcategory_list[0] if isinstance(subcategory_list, list) and subcategory_list else ""  # → '["곱창","막창"]' 형태

            all_comments = []

            # 원본 data에서 해당 식당명으로 각 플랫폼 리뷰 수집
            sources = data.get(name, {})
            for platform_key in ["naver", "catchtable", "kakaomap"]:
                entries = sources.get(platform_key, [])
                for entry in entries:
                    comment_data = entry.get("data", {}).get("comment", [])
                    if isinstance(comment_data, list):
                        for item in comment_data:
                            if isinstance(item, str):
                                all_comments.append(item)
                            elif isinstance(item, list):
                                all_comments.extend(str(x) for x in item if isinstance(x, str))

            # HTML 속성용으로 변환
            comment_html = "<br>".join(
                str(c) if isinstance(c, str) else "<br>".join(map(str, c))
                for c in all_comments
            ).replace('"', '&quot;').replace("'", "&#39;")

            score = str(info.get("rating", "0.0")).strip()
            if score in ["0", "0.0"]:
                score_html = ""
            else:
                score_html = f'''
                    <div class="star-icon"><img src="/static/star-icon.png"/></div>
                    <div class="restaurant-score">{score}</div>
                '''

            address = info.get("address", "주소 정보 없음")
            review_count = info.get("total_reviews", 0)

            out.write(f'''
            <div class="content-card" data-category="{category}" data-subcategory="{subcategory}" data-comment="{comment_html}" onclick="handleCardClick({idx + 1})" role="button" tabindex="0" aria-label="콘텐츠 카드 {idx + 1}">
                <button <button class="prefs-button" aria-label="액션 버튼">
                  <img src="/static/prefs_button.png" alt="선호 버튼" class="prefs-button-icon">
                    </button>
                {score_html}
                <div class="review-count">{review_count}개 리뷰</div>
                <div class="restaurant-name">{name}</div>
                <div class="restaurant-category">{category}</div>
                <div class="restaurant-address">{address}</div>
            </div>
            ''')

        # 카드 컨테이너 닫기 및 나머지 레이아웃
        out.write("""
            </div>
            <div class="divider-line-2"></div>
            <div class="review-container"></div>
        </div>

        <div class="debug-info" id="debugInfo">
            <div>Screen: <span id="screenSize"></span></div>
            <div>Scale: <span id="scaleValue"></span></div>
        </div>

        <script>
    document.addEventListener("DOMContentLoaded", () => {
        const cards = document.querySelectorAll('.content-card');
        const reviewBox = document.querySelector('.review-container');

        cards.forEach((card) => {
            const prefsButton = card.querySelector('.prefs-button');

            // ✅ 선호 버튼 이벤트 (클릭 시 config.py 업데이트)
            if (prefsButton) {
                prefsButton.addEventListener("click", (e) => {
                    e.stopPropagation(); // 카드 클릭 막기

                    const subcategory = card.getAttribute('data-subcategory') || '';
                    console.log("⭐ 선호 gkdnl카테고리:", subcategory);

                    fetch("/update_weight", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ subcategory })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            alert(`'${subcategory}' 가중치 +0.2`);
                        } else {
                            alert("업데이트 실패");
                        }
                    })
                    .catch(err => {
                        console.error("서버 오류:", err);
                        alert("서버 통신 실패");
                    });
                });
            }

            // ✅ 카드 클릭 이벤트 (리뷰 로딩)
            card.addEventListener("click", () => {
                cards.forEach(c => c.classList.remove("clicked"));
                card.classList.add("clicked");

                const comment = card.getAttribute('data-comment') || '';
                reviewBox.innerHTML = comment
                    ? comment  // 이미 <br> 있음
                    : '<span style="color:#000">리뷰가 없습니다.</span>';
            });
        });
    });


        function handleNavigation(buttonNumber) {
            const categories = ["한식", "양식", "일식", "중식", "아시아음식", "카페·베이커리", "주점", "기타"];
            const selectedCategory = categories[buttonNumber - 1];

            const container = document.querySelector('.content-card-scroll');
            const cards = Array.from(document.querySelectorAll('.content-card'));

            // 선택된 카테고리의 카드들 먼저
            const matched = cards.filter(card => card.getAttribute('data-category') === selectedCategory);
            const unmatched = cards.filter(card => card.getAttribute('data-category') !== selectedCategory);

            // 기존 카드 제거
            container.innerHTML = '';

            // 순서대로 다시 추가
            matched.concat(unmatched).forEach(card => container.appendChild(card));
        }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                if (e.target.classList.contains('content-card')) {
                    e.preventDefault();
                    e.target.click();
                }
            }
        });
        
        function updateDebugInfo() {
            const debugInfo = document.getElementById('debugInfo');
            const screenSize = document.getElementById('screenSize');
            const scaleValue = document.getElementById('scaleValue');

            if (debugInfo && screenSize && scaleValue) {
                screenSize.textContent = `${window.innerWidth} x ${window.innerHeight}`;
                let scale = window.innerWidth <= 1920 ? window.innerWidth / 1920 : 1;
                if (window.innerWidth <= 1400) scale = 0.7;
                if (window.innerWidth <= 1000) scale = 0.5;
                if (window.innerWidth <= 768) scale = 0.4;
                scaleValue.textContent = scale.toFixed(2);
            }
        }

        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'd') {
                e.preventDefault();
                const debugInfo = document.getElementById('debugInfo');
                debugInfo.style.display = debugInfo.style.display === 'block' ? 'none' : 'block';
                if (debugInfo.style.display === 'block') {
                    updateDebugInfo();
                }
            }
        });

        window.addEventListener('resize', updateDebugInfo);
        window.addEventListener('load', updateDebugInfo);
        </script>
    </body>
    </html>
    """)
