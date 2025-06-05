# JSON 데이터를 기반으로 식당 정보를 HTML로 렌더링하는 스크립트
import json

with open("reviews_NM.json", encoding="utf-8") as f:
    data = json.load(f)

with open("result.html", "w", encoding="utf-8") as out:
    out.write("""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>식당 결과 페이지</title>
    <link rel="stylesheet" href="results.css">
</head>
<body>
    <div class="main-frame">
        <!-- 상단 헤더 -->
        <div class="banner"></div>

        <!-- 네비게이션 버튼들 -->
        <button class="category category-1" onclick="handleNavigation(1)" aria-label="네비게이션 버튼 1">
            <span class="category-text">한식</span>
        </button>
        <button class="category category-2" onclick="handleNavigation(2)" aria-label="네비게이션 버튼 2">
            <span class="category-text">양식</span>
        </button>
        <button class="category category-3" onclick="handleNavigation(3)" aria-label="네비게이션 버튼 3">
            <span class="category-text">일식</span>
        </button>
        <button class="category category-4" onclick="handleNavigation(4)" aria-label="네비게이션 버튼 4">
            <span class="category-text">중식</span>
        </button>
        <button class="category category-5" onclick="handleNavigation(5)" aria-label="네비게이션 버튼 5">
            <span class="category-text">아시안</span>
        </button>
        <button class="category category-6" onclick="handleNavigation(6)" aria-label="네비게이션 버튼 6">
            <span class="category-text">기타</span>
        </button>

        <!-- 첫 번째 구분선 -->
        <div class="divider-line-1"></div>

        <!-- 콘텐츠 카드들 -->
        <div class="content-card-scroll" style="overflow-y: hidden;">
""")
    for idx, (name, info) in enumerate(data.items()):
        comment_text = '<br>'.join(info.get("comment", []))
        comment_text_escaped = comment_text.replace('"', '&quot;').replace("'", "&#39;")
        out.write(f'''
            <div class="content-card" data-comment="{comment_text_escaped}" onclick="handleCardClick({idx + 1})" role="button" tabindex="0" aria-label="콘텐츠 카드 {idx + 1}">
                <div class="star-icon"><img src="star-icon.png"/></div>
                <div class="restaurant-score">{info.get("average_rating", "0.0")}</div>
                <div class="restaurant-name">{name}</div>
                <div class="restaurant-category">{info.get("category", "0")}</div>
                <div class="restaurant-address">{info.get("address", "0")}</div>
            </div>
        ''')
    out.write("""
        </div>

        <!-- 두 번째 구분선 -->
        <div class="divider-line-2"></div>

        <!-- 하단 영역 -->
        <div class="review-container"></div>
    </div>

    <!-- 디버그 정보 (개발용) -->
    <div class="debug-info" id="debugInfo">
        <div>Screen: <span id="screenSize"></span></div>
        <div>Scale: <span id="scaleValue"></span></div>
    </div>

    <script>
        // 네비게이션 버튼 클릭 핸들러
        function handleNavigation(buttonNumber) {
            console.log(`네비게이션 버튼 ${buttonNumber} 클릭됨`);
            
            // 버튼 활성화 효과
            const button = document.querySelector(`.category-${buttonNumber}`);
            button.style.backgroundColor = '#BBBBBB';
            setTimeout(() => {
                button.style.backgroundColor = '#D9D9D9';
            }, 200);

            // 실제 네비게이션 로직을 여기에 추가
            alert(`네비게이션 ${buttonNumber}번이 클릭되었습니다.`);
        }

        // 카드 클릭 핸들러
        function handleCardClick(cardNumber) {
            // 클릭한 카드 그림자 효과
            const cards = document.querySelectorAll('.content-card');
            cards.forEach(card => card.style.boxShadow = "none");
            const clicked = cards[cardNumber-1];
            if (clicked) clicked.style.boxShadow = "0 8px 25px rgba(0,0,0,0.2)";

            // data-comment 속성에서 리뷰 불러와서 review-container에 표시
            const reviewBox = document.querySelector('.review-container');
            if (clicked && reviewBox) {
                const comment = clicked.getAttribute('data-comment') || '';
                reviewBox.innerHTML = comment
                    ? comment.replace(/\\n/g, '<br>')
                    : '<span style="color:#888">리뷰가 없습니다.</span>';
            }
        }

        // 키보드 접근성
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                if (e.target.classList.contains('content-card')) {
                    e.preventDefault();
                    const cards = Array.from(document.querySelectorAll('.content-card'));
                    const cardNumber = cards.indexOf(e.target) + 1;
                    if (cardNumber) {
                        handleCardClick(cardNumber);
                    }
                }
            }
        });

        // 반응형 디버깅 (개발용)
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

        // 디버그 토글 (Ctrl + D)
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