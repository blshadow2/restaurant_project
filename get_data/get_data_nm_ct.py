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
        print("🚀 캐치테이블 페이지 접속 중...")
        driver.get("https://app.catchtable.co.kr/ct/login")
        time.sleep(2)
        driver.find_element(By.XPATH, '//*[@id="root"]/div[2]/main/section/div[2]/div/div/div/button[3]').click()
        time.sleep(1)
        driver.find_element(By.XPATH, '//*[@id="login-id"]').send_keys(ct_id)
        driver.find_element(By.XPATH, '//*[@id="login-pw"]').send_keys(ct_pw + Keys.ENTER)
        time.sleep(3)

        if "login" in driver.current_url:
            print("❌ 로그인 실패: 아이디 또는 비밀번호 확인 필요")
            driver.quit()
            return

        try:
            driver.find_element(By.XPATH, '//*[@id="popup"]/div/div/div/div/div[2]/button[1]').click()
        except:
            pass

        driver.find_element(By.XPATH, '//*[@id="root"]/div[3]/div/a').click()
        driver.find_element(By.XPATH, '//*[@id="header"]/div/form/input').click()
        time.sleep(1)
        driver.find_element(By.XPATH, '//*[@id="header"]/div/div/div/input').send_keys(location)
        time.sleep(2)

        try:
            count_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div[1]/div/div/div[1]/span'))
            )
            restaurant_count = int(count_elem.text.replace(",", ""))
        except:
            print("❌ 음식점 수 확인 실패")
            driver.quit()
            return

        driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div').click()
        time.sleep(3)

        reviews = {}
        for i in range(restaurant_count):
            try:
                elme = driver.find_element(By.XPATH, f'//*[@id="virtual_{i}"]')
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elme)
                name_elem = elme.find_element(By.XPATH, './/p')
                name = name_elem.text.strip() or f"이름없음_{i}"
                print(f"[{i+1}] {name}")
                elme.click()
                time.sleep(2)

                try:
                    driver.find_element(By.XPATH, '//*[@id="popup"]/div/div/div/div/div/button[1]').click()
                except:
                    pass

                tab_nav = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="wrapperDiv"]/nav/ul'))
                )
                for tab in tab_nav.find_elements(By.TAG_NAME, 'li'):
                    if "리뷰" in tab.text:
                        tab.click()
                        break
                time.sleep(1)

                comments = []
                for j in range(1, 11):
                    try:
                        rating = driver.find_element(By.XPATH, f'//*[@id="main"]/div[2]/div/div/div/div[{j}]/article/div[1]/div[2]/div/a/div').text
                        comment = driver.find_element(By.XPATH, f'//*[@id="main"]/div[2]/div/div/div/div[{j}]/article/div[2]/div[2]/p').text
                        if len(comment.strip()) >= 10:
                            comments.append((rating, comment))
                    except:
                        break

                reviews[name] = comments
                driver.back()
                time.sleep(1)
                driver.back()
                time.sleep(1)

            except Exception as e:
                print(f"[{i+1}] ❌ 오류 발생: {e}")

        with open(f'reviews_CT_{location}.json', 'w', encoding='utf-8') as f:
            json.dump(reviews, f, ensure_ascii=False, indent=4)
        print("✅ 캐치테이블 저장 완료")

# 예시 실행
collect_reviews('naver', '서대문구')
# collect_reviews('catchtable', '서대문구', ct_id='01067017382', ct_pw='xorehd123!')
