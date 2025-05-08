from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import pandas as pd

options = Options()
options.add_argument('--start-maximized')
options.add_argument('--disable-blink-features=AutomationControlled')

driver = webdriver.Chrome(options=options)

# 네이버 지도 접속
driver.get("https://map.naver.com/v5/search/서대문구%20음식점")

time.sleep(10)  # 페이지 로딩 대기

# iframe 안으로 이동 (지도는 iframe으로 구성됨)
driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR, "iframe#searchIframe"))

results = []
scrolls = 0

while len(results) < 1000 and scrolls < 100: 
    time.sleep(1)
    
    items = driver.find_elements(By.CSS_SELECTOR, 'li .place_bluelink')  # 상호명 링크
    for item in items:
        try:
            name = item.text
            parent = item.find_element(By.XPATH, "..").find_element(By.XPATH, "..")
            addr = parent.find_element(By.CLASS_NAME, 'place_blind').text
            reviews = parent.text.split('\n')
            review_count = next((r for r in reviews if '리뷰' in r), '리뷰 0').replace('리뷰', '').strip()
            
            results.append({
                '상호명': name,
                '주소': addr,
                '리뷰수': review_count
            })
        except:
            continue

    # 스크롤해서 더 많은 가게 불러오기
    driver.execute_script("window.scrollBy(0, 1000);")
    scrolls += 1

# 중복 제거
df = pd.DataFrame(results).drop_duplicates(subset=["상호명", "주소"])

# 리뷰 많은 순 정렬
df["리뷰수"] = df["리뷰수"].str.replace(",", "").astype(int)
df = df.sort_values(by="리뷰수", ascending=False).head(1000)

# 저장
df.to_csv("seodaemun_top1000_food.csv", index=False, encoding="utf-8-sig")

driver.quit()

# 코드를 공부해서 수정해보자.