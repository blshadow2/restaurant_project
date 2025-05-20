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


def create_driver():
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
    return webdriver.Chrome(options=options)


def collect_data(source, location, ct_id=None, ct_pw=None):
    os.chdir(os.path.dirname(__file__))
    driver = create_driver()

    if source == 'naver':
        print("\n🚀 네이버 지도 데이터 수집 시작")
        driver.get(f"https://map.naver.com/p/search/{location} 맛집")
        time.sleep(2)
        driver.switch_to.frame(driver.find_element(By.ID, 'searchIframe'))

        scrollable = driver.find_element(By.XPATH, '//*[@id="_pcmap_list_scroll_container"]')
        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable)

        while True:
            driver.execute_script("arguments[0].scrollTop += 1000;", scrollable)
            time.sleep(1)
            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable)
            if new_height == last_height:
                break
            last_height = new_height

        reviews = {}
        restaurants = driver.find_elements(By.CSS_SELECTOR, 'li[data-laim-exp-id="undefinedundefined"]')

        for index, li in enumerate(restaurants):
            try:
                name = li.find_element(By.XPATH, ".//span[contains(@class, 'TYaxT')]").text.strip()
                category = li.find_element(By.XPATH, ".//span[contains(@class, 'KCMnt')]").text.strip()
                li.find_element(By.XPATH, ".//a").click()
                time.sleep(2)
                driver.switch_to.default_content()
                driver.switch_to.frame(driver.find_element(By.ID, 'entryIframe'))

                tab_parent = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="app-root"]/div/div/div/div[4]/div/div/div/div'))
                )
                for tab in tab_parent.find_elements(By.TAG_NAME, 'a'):
                    if "리뷰" in tab.text:
                        tab.click()
                        break
                time.sleep(2)

                comments = []
                for r in driver.find_elements(By.CSS_SELECTOR, 'ul li')[:10]:
                    comments.append(r.text.strip())

                reviews[name] = {"category": category, "comment": comments}
            except:
                continue
            finally:
                driver.switch_to.default_content()
                driver.switch_to.frame(driver.find_element(By.ID, 'searchIframe'))

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

        driver.find_element(By.XPATH, '//*[@id="popup"]/div/div/div/div/div[2]/button[1]').click()
        driver.find_element(By.XPATH, '//*[@id="root"]/div[3]/div/a').click()
        driver.find_element(By.XPATH, '//*[@id="header"]/div/form/input').click()
        time.sleep(1)
        driver.find_element(By.XPATH, '//*[@id="header"]/div/div/div/input').send_keys(location)
        time.sleep(2)
        driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div').click()
        time.sleep(3)

        handle = driver.find_element(By.CSS_SELECTOR, '#status-bar-open-map > div > div.modal-location > div:nth-child(2) > div._53lcbm0._53lcbm2 > div.xnbnj35')
        ActionChains(driver).click_and_hold(handle).move_by_offset(0, -300).release().perform()
        time.sleep(2)

        print("⚠️ 캐치테이블 상세 리뷰 수집 로직은 생략되었으며, 필요한 경우 통합 코드 확장 가능")
        with open(f'reviews_CT_{location}.json', 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        print("✅ 캐치테이블 저장 완료")

    driver.quit()
    print("🛑 드라이버 종료 완료")


# 사용 예시:
collect_data('naver', '서대문구')
# collect_data('catchtable', '서대문구', ct_id='your_id', ct_pw='your_pw')
