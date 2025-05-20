import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

os.chdir(os.path.dirname(__file__))

# 크롬 옵션 설정
options = Options()
user_agent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)
options.add_argument(f"user-agent={user_agent}")
options.add_argument("--headless")  # 헤드리스 모드 (브라우저 창 안 뜨게 함)
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--window-size=1920,1080")  

driver = webdriver.Chrome(options=options)

def get_data(nm):
    print("🚀 네이버 지도 페이지 접속 중...")
    driver.get("https://map.naver.com/p/search/서대문구 맛집?c=13.00,0,0,0,dh")
    time.sleep(1)

    # 검색결과 iframe 진입
    search_frame = driver.find_element(By.ID, 'searchIframe')
    driver.switch_to.frame(search_frame)

    # 스크롤 하여 음식점 리스트 모두 로딩
    scrollable_element = driver.find_element(By.XPATH, '//*[@id="_pcmap_list_scroll_container"]')
    last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_element)

    scroll_count = 0
    while True:
        driver.execute_script("arguments[0].scrollTop += 1200;", scrollable_element)
        time.sleep(1)
        new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_element)
        if new_height == last_height:
            break
        last_height = new_height
        scroll_count += 1
        print(f"🔄 스크롤 {scroll_count}회차 완료")

    reviews = {}
    restaurants = driver.find_elements(By.CSS_SELECTOR, 'li[data-laim-exp-id="undefinedundefined"]')
    print(f"📋 수집 대상 음식점 수: {len(restaurants)}개")

    for index, li in enumerate(restaurants):
        try:
            name_elem = li.find_element(By.XPATH, ".//div[1]/div[1]/a/span[contains(@class, 'TYaxT')]")
            category_elem = li.find_element(By.XPATH, ".//div[1]/div[1]/a/span[contains(@class, 'KCMnt')]")
            button = li.find_element(By.XPATH, ".//div[1]/div[1]/a")
        except Exception as e:
            print(f"❌ [{index+1}] 음식점 요소 수집 실패: {e}")
            continue

        name = name_elem.text.strip()
        category = category_elem.text.strip()
        print(f"▶ {index+1}/{len(restaurants)}: {name} ({category})")

        reviews[name] = {"category": category}

        # 상세 페이지 클릭
        try:
            button.click()
            time.sleep(2)
            driver.switch_to.default_content()
            driver.switch_to.frame(driver.find_element(By.ID, 'entryIframe'))

            # 리뷰 탭 클릭
            try:
                parent = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="app-root"]/div/div/div/div[4]/div/div/div/div'))
                )
                tab_links = parent.find_elements(By.TAG_NAME, 'a')
                for tab in tab_links:
                    if "리뷰" in tab.text:
                        tab.click()
                        break
            except:
                print("   ⚠️ 리뷰 탭 없음 — 스킵")
                continue

            # 리뷰 수집 (최대 10개)
            comments = []
            time.sleep(2)
            try:
                review_items = WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'ul li'))
                )
            except:
                review_items = []

            for li in review_items[:10]:
                try:
                    text = li.text.strip()
                    if text:
                        comments.append(text)
                except:
                    continue

            reviews[name]["comment"] = comments
            print(f"   ✔ 리뷰 {len(comments)}개 수집 완료")

        except Exception as e:
            print(f"   ❌ 상세 페이지 수집 중 에러: {e}")
            continue

        finally:
            driver.switch_to.default_content()
            driver.switch_to.frame(search_frame)

    # 결과 저장
    with open('reviews_NM.json', 'w', encoding='utf-8') as f:
        json.dump(reviews, f, ensure_ascii=False, indent=4)

    print("\n✅ 모든 음식점 정보 수집 완료 및 저장 완료!")

# 실행
get_NM_data()
