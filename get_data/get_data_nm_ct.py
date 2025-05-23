
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
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("detach", True)
    if headless:
        options.add_argument("--headless")
    return webdriver.Chrome(options=options)

def close_popup(driver):
    try:
        popup = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="popup"]/div/div/div/div/div/button[1]'))
        )
        popup.click()
        print("🔻 팝업 닫힘")
    except:
        pass

def collect_reviews(source, location, ct_id=None, ct_pw=None):
    os.chdir(os.path.dirname(__file__))
    driver = create_driver(headless=(source == 'naver'))

    if source == 'catchtable':
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

        close_popup(driver)

        driver.find_element(By.XPATH, '//*[@id="root"]/div[3]/div/a').click()
        driver.find_element(By.XPATH, '//*[@id="header"]/div/form/input').click()
        time.sleep(1)
        driver.find_element(By.XPATH, '//*[@id="header"]/div/div/div/input').send_keys(location)
        time.sleep(2)

        restaurant_count = driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div/div/div[1]/span').text
        print(f"✅ 검색된 음식점 수: {restaurant_count}")
        driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div').click()
        time.sleep(3)

        reviews = {}
        for i in range(int(restaurant_count)):
            try:
                elme = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f'//*[@id="virtual_{i}"]'))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elme)
                time.sleep(1)

                restaurant = elme.find_element(By.XPATH, './/p').text.strip()
                reviews[restaurant] = []

                print(f"[{i+1}] {restaurant}")
                elme.click()
                time.sleep(2)

                close_popup(driver)

                tab_nav = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="wrapperDiv"]/nav/ul'))
                )
                tabs = tab_nav.find_elements(By.TAG_NAME, 'li')

                review_tab_found = False
                for tab in tabs:
                    if "리뷰" in tab.text:
                        try:
                            tab.click()
                            review_tab_found = True
                            break
                        except Exception:
                            # 광고가 클릭을 막을 경우 빈공간 클릭 후 재시도
                            ActionChains(driver).move_by_offset(300, 300).click().perform()
                            time.sleep(1)
                            try:
                                tab.click()
                                review_tab_found = True
                                print("✅ 광고 우회 후 리뷰탭 클릭 성공")
                                break
                            except:
                                print("⛔ 리뷰탭 우회 클릭 실패")

                if not review_tab_found:
                    print("⛔ 리뷰탭 없음 — 뒤로가기")
                    driver.back()
                    time.sleep(1)
                    driver.back()
                    time.sleep(1)
                    close_popup(driver)
                    continue

                time.sleep(1)

                try:
                    parent = driver.find_element(By.XPATH, '//*[@id="main"]/div[2]/div/div/div')
                except:
                    parent = driver.find_element(By.XPATH, '//*[@id="main"]/div[3]/div/div/div')

                count = driver.execute_script("return arguments[0].childElementCount;", parent)

                review_counter = 0
                for j in range(1, count + 1):
                    if review_counter >= 5:
                        break
                    try:
                        rating = driver.find_element(By.XPATH, f'//*[@id="main"]/div[2]/div/div/div/div[{j}]/article/div[1]/div[2]/div/a/div').text
                        comment = driver.find_element(By.XPATH, f'//*[@id="main"]/div[2]/div/div/div/div[{j}]/article/div[2]/div[2]/p').text
                    except:
                        try:
                            rating = driver.find_element(By.XPATH, f'//*[@id="main"]/div[3]/div/div/div/div[{j}]/article/div[1]/div[2]/div/a/div').text
                            comment = driver.find_element(By.XPATH, f'//*[@id="main"]/div[3]/div/div/div/div[{j}]/article/div[2]/div[2]/p').text
                        except:
                            continue
                    if len(comment.strip()) >= 10:
                        reviews[restaurant].append((rating, comment))
                        review_counter += 1

                driver.back()
                time.sleep(1)
                driver.back()
                time.sleep(1)
                close_popup(driver)

            except Exception as e:
                print(f"[{i+1}] 오류 발생: {e}")
                continue

        with open(f'reviews_CT_{location}.json', 'w', encoding='utf-8') as f:
            json.dump(reviews, f, ensure_ascii=False, indent=4)
        print("✅ 캐치테이블 저장 완료")

if __name__ == '__main__':
    source = input("사이트를 입력하세요 (naver/catchtable): ").strip().lower()
    location = input("지역명을 입력하세요 (예: 서대문구): ").strip()
    if source == 'catchtable':
        ct_id = input("캐치테이블 ID를 입력하세요: ").strip()
        ct_pw = input("캐치테이블 비밀번호를 입력하세요: ").strip()
        collect_reviews(source, location, ct_id, ct_pw)
    elif source == 'naver':
        collect_reviews(source, location)
    else:
        print("지원하지 않는 사이트입니다. 'naver' 또는 'catchtable'을 입력하세요.")
