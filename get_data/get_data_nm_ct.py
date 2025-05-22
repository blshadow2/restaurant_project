import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def create_driver(headless=False):
    options = Options()
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("detach", True)
    if headless:
        options.add_argument("--headless")
    return webdriver.Chrome(options=options)

def collect_reviews(source, location, ct_id=None, ct_pw=None):
    os.chdir(os.path.dirname(__file__))
    driver = create_driver(headless=(source == 'naver'))

    if source == 'naver':
        print("🚀 네이버 지도 페이지 접속 중...")
        driver.get(f"https://map.naver.com/p/search/{location} 맛집")
        time.sleep(1)
        search_frame = driver.find_element(By.ID, 'searchIframe')
        driver.switch_to.frame(search_frame)

        scrollable_element = driver.find_element(By.XPATH, '//*[@id="_pcmap_list_scroll_container"]')
        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_element)

        while True:
            driver.execute_script("arguments[0].scrollTop += 1200;", scrollable_element)
            time.sleep(1)
            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_element)
            if new_height == last_height:
                break
            last_height = new_height

        reviews = {}
        restaurants = driver.find_elements(By.CSS_SELECTOR, 'li[data-laim-exp-id="undefinedundefined"]')
        print(f"📋 수집 대상 음식점 수: {len(restaurants)}개")

        for index, li in enumerate(restaurants):
            try:
                name_elem = li.find_element(By.XPATH, ".//span[contains(@class, 'TYaxT')]")
                category_elem = li.find_element(By.XPATH, ".//span[contains(@class, 'KCMnt')]")
                button = li.find_element(By.XPATH, ".//a")
                name = name_elem.text.strip()
                category = category_elem.text.strip()
                reviews[name] = {"category": category}

                button.click()
                time.sleep(2)
                driver.switch_to.default_content()
                driver.switch_to.frame(driver.find_element(By.ID, 'entryIframe'))

                try:
                    parent = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="app-root"]/div/div/div/div[4]/div/div/div/div'))
                    )
                    for tab in parent.find_elements(By.TAG_NAME, 'a'):
                        if "리뷰" in tab.text:
                            tab.click()
                            break
                    time.sleep(2)
                    review_items = driver.find_elements(By.CSS_SELECTOR, 'ul li')
                    comments = [li.text.strip() for li in review_items[:10] if li.text.strip()]
                    reviews[name]["comment"] = comments
                    print(f"   ✔ {name} 리뷰 {len(comments)}개 수집 완료")
                except:
                    print(f"   ⚠️ {name} 리뷰 없음 — 스킵")

            except Exception as e:
                print(f"❌ {index+1}번 오류: {e}")
            finally:
                driver.switch_to.default_content()
                driver.switch_to.frame(search_frame)

        with open(f'reviews_NM_{location}.json', 'w', encoding='utf-8') as f:
            json.dump(reviews, f, ensure_ascii=False, indent=4)
        print("✅ 네이버 저장 완료")

    elif source == 'catchtable':
        print("\n🚀 캐치테이블 데이터 수집 시작")
        driver.get("https://app.catchtable.co.kr/ct/login")
        time.sleep(2)
        driver.find_element(By.XPATH, '//*[@id="root"]/div[2]/main/section/div[2]/div/div/div/button[3]').click()
        time.sleep(1)
        driver.find_element(By.XPATH, '//*[@id="login-id"]').send_keys(ct_id)
        driver.find_element(By.XPATH, '//*[@id="login-pw"]').send_keys(ct_pw + Keys.ENTER)
        time.sleep(3)

        if "login" in driver.current_url:
            print("❌ 로그인 실패: 아이디 또는 비밀번호를 확인하세요.")
            driver.quit()
            return

        driver.find_element(By.XPATH, '//*[@id="popup"]/div/div/div/div/div[2]/button[1]').click()
        driver.find_element(By.XPATH, '//*[@id="root"]/div[3]/div/a').click()
        driver.find_element(By.XPATH, '//*[@id="header"]/div/form/input').click()
        time.sleep(1)
        driver.find_element(By.XPATH, '//*[@id="header"]/div/div/div/input').send_keys(location)
        time.sleep(2)

        restaurant_count=driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div/div/div[1]/span').text
        print(restaurant_count)
        driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div').click()

        time.sleep(3)
        handle = driver.find_element(By.CSS_SELECTOR, '#status-bar-open-map > div > div.modal-location > div:nth-child(2) > div._53lcbm0._53lcbm2 > div.xnbnj35')

        actions = ActionChains(driver)
        actions.click_and_hold(handle) \
            .move_by_offset(0, -300) \
            .release() \
            .perform()
        time.sleep(3)
        
        
        reviews = {}
        for i in range(int(restaurant_count)):
            
            try:
                elme = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f'//*[@id="virtual_{i}"]'))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elme)
                time.sleep(1)  # 렌더링 대기

                # 평점 div가 없으면 스킵 (XPath로 확인)
                try:
                    elme.find_element(By.XPATH, './/div[contains(@class, "Rating_rating__")]')
                except:
                    print(f"[{i+1}] 평점 없음 → 스킵")
                    continue

                # 텍스트 로드 완료까지 기다리기
                restaurant_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f'//*[@id="virtual_{i}"]/div/div/div[1]/div/div/div[1]/div[1]/p'))
                )
                restaurant = restaurant_elem.text.strip()

                #가게 이름 저장
                reviews[restaurant] = []

                if not restaurant:
                    print(f"[{i+1}] 이름 비어 있음 (렌더링 안 됨)")
                    continue

                print(f"[{i+1}] {restaurant}")
                elme.click()  # 음식점 클릭
                time.sleep(2)

                # 음식점 상세 페이지 들어간 직후
                try:
                    WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[text()="다시 보지 않기"]'))
                    ).click()
                    print("🧼 팝업 '다시 보지 않기' 클릭 완료")
                except:
                    pass  # 팝업이 없으면 그냥 넘어감

                # 팝업 '오늘 그만 보기' 버튼이 있으면 클릭
                try:
                    today_close_btn = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[text()="오늘 그만 보기"]'))
                    )
                    today_close_btn.click()
                    print("🧼 팝업 '오늘 그만 보기' 클릭 완료")
                    time.sleep(1)
                except:
                    pass  # 팝업이 없으면 무시



                

            except Exception as e:
                print(f"[{i+1}] 오류 발생: {e}")
                continue

            # 팝업 닫기
            try:
                driver.find_element(By.XPATH, '//*[@id="popup"]/div/div/div/div/div/button[1]').click()
            except:
                pass

            tab_nav = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="wrapperDiv"]/nav/ul'))
            )
            tabs = tab_nav.find_elements(By.TAG_NAME, 'li')
            for tab in tabs:
                if "리뷰" in tab.text:
                    tab.click()
                    break
            time.sleep(1)

            parent = WebDriverWait(driver, 10).until( EC.presence_of_element_located((By.XPATH, '//*[@id="wrapperDiv"]/nav/ul'))) 
            count=driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > li').length;", parent)

            try:
                    parent=driver.find_element(By.XPATH, '//*[@id="main"]/div[2]/div/div/div')
            except:
                    parent=driver.find_element(By.XPATH, '//*[@id="main"]/div[3]/div/div/div')
            count = 0

            #리뷰 수집
            comments = []
            try:
                if driver.find_element(By.CSS_SELECTOR, '#main > div._7xsxe00 > label > div > span.mmxont2._1ltqxco1h.mmxont4').text == "블로그 리뷰":  # 자체 리뷰가 없을 경우
                    driver.back()
                    time.sleep(1)
                    driver.back()
                    reviews[restaurant].append('none')
                    continue
            except:
                pass

            coment_count = driver.find_element(By.XPATH, '//*[@id="main"]/section[1]/div/div/div[1]/h5/span').text
            coment_count = coment_count.split('개')[0].replace(",", "")  # ← 쉼표 제거 추가
            coment_count = int(coment_count)  # 문자열 → 숫자 변환

            if int(coment_count) > 24:  # 댓글이 24개 이상일 경우
                while count < 24:  # 댓글 로딩
                    driver.execute_script("window.scrollBy(0, 100);")
                    count = driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > div').length;", parent)
            else:
                while count < int(coment_count):  # 댓글 로딩
                    driver.execute_script("window.scrollBy(0, 100);")
                    count = driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > div').length;", parent)

            for j in range(1, count):  # 댓글 크롤링
                try:
                    rating = driver.find_element(
                        By.XPATH,
                        '//*[@id="main"]/div[2]/div/div/div/div[{}]/article/div[1]/div[2]/div/a/div'.format(j)
                    ).text
                    try:
                        coment = driver.find_element(
                            By.XPATH,
                            '//*[@id="main"]/div[2]/div/div/div/div[{}]/article/div[2]/div[2]/p'.format(j)
                        ).text
                    except:
                        coment = ''
                except:
                    rating = driver.find_element(
                        By.XPATH,
                        '//*[@id="main"]/div[3]/div/div/div/div[{}]/article/div[1]/div[2]/div/a/div'.format(j)
                    ).text
                    try:
                        coment = driver.find_element(
                            By.XPATH,
                            '//*[@id="main"]/div[3]/div/div/div/div[{}]/article/div[2]/div[2]/p'.format(j)
                        ).text
                    except:
                        coment = ''

                if len(coment.strip()) >= 10:
                    reviews[restaurant].append((rating, coment))

            driver.back()
            time.sleep(1)
            try:
                driver.find_element(By.XPATH, '//a[text()="뒤로"]').click()
            except Exception as e:
                print(f"❌ '뒤로' 버튼 클릭 실패: {type(e).__name__} - {e}")
            time.sleep(1)
            

        with open(f'reviews_CT_{location}.json', 'w', encoding='utf-8') as f:
            json.dump(reviews, f, ensure_ascii=False, indent=4)
        print("✅ 캐치테이블 저장 완료")

if __name__ == '__main__':
    source = input("사이트를 입력하세요 (naver/catchtable): ").strip().lower()
    location = input("지역명을 입력하세요 (예: 서대문구): ").strip()
    if source == 'catchtable':
        ct_id = input("캐치테이블 ID를 입력하세요: ").strip()
        ct_pw = input("캐치테이블 비밀번호를 입력하세요: ").strip()
        collect_data(source, location, ct_id, ct_pw)
    elif source == 'naver':
        collect_data(source, location)
    else:
        print("지원하지 않는 사이트입니다. 'naver' 또는 'catchtable'을 입력하세요.")


# 예시 실행
collect_reviews('naver', '서대문구')
# collect_reviews('catchtable', '서대문구', ct_id='01067017382', ct_pw='xorehd123!')
