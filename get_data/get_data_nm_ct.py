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
    restaurant_count=driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div/div/div[1]/span').text

    

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

        #드래그
    for i in range(int(restaurant_count)):
        elements=driver.find_elements(By.CSS_SELECTOR, f'#virtual_{i} > div > div > div.ShopListItem_topInfoBox__1p45wh61 > div > div > div.ShopListItem_infoBox__1p45wh63 > div.ShopHeaderInfo_box__1lnb8ff0 > div')
        if not elements: # 리뷰가 없는 경우 다음으로
            reviews[restaurant].append('none')
            continue
        try: # 음식점 페이지 진입 & 특정 항목에 처음 진입시 팝업해결
            elems=driver.find_element(By.XPATH, '//*[@id="virtual_{}"]/div/div/div[1]/div/div[1]/div/div/div/button/span'.format(i))
        except:
            elems=False
        if elems: 
            if elems.text =="위스키 페어링 맛집" and flag==0:
                restaurant=driver.find_element(By.XPATH, '//*[@id="virtual_{}"]/div/div/div[1]/div/div/div[1]/div[1]/p'.format(i)).text
                print(restaurant)
                elme=driver.find_element(By.XPATH, '//*[@id="virtual_{}"]'.format(i))
                # 1) 클릭할 요소를 찾고
                # 2) 화면 안에 보이도록 스크롤 (부모 컨테이너가 virtualized list)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",elme)
                time.sleep(0.3)  # 렌더링 안정화
                elme.click()
                time.sleep(1)
                driver.find_element(By.XPATH, '//*[@id="popup"]/div/div/div/div/div/button[1]').click()
                flag=1
            else:
                restaurant=driver.find_element(By.XPATH, '//*[@id="virtual_{}"]/div/div/div[1]/div/div/div[1]/div[1]/p'.format(i)).text
                print(restaurant)
                elme=driver.find_element(By.XPATH, '//*[@id="virtual_{}"]'.format(i))
                # 1) 클릭할 요소를 찾고
                # 2) 화면 안에 보이도록 스크롤 (부모 컨테이너가 virtualized list)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",elme)
                time.sleep(0.3)  # 렌더링 안정화
                elme.click()
                
        else:        
            restaurant=driver.find_element(By.XPATH, '//*[@id="virtual_{}"]/div/div/div[1]/div/div/div[1]/div[1]/p'.format(i)).text
            print(restaurant)
            elme=driver.find_element(By.XPATH, '//*[@id="virtual_{}"]'.format(i))
            # 1) 클릭할 요소를 찾고
            # 2) 화면 안에 보이도록 스크롤 (부모 컨테이너가 virtualized list)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",elme)
            time.sleep(0.3)  # 렌더링 안정화
            elme.click()
        reviews[restaurant]=[]
        #리뷰창 진입
        parent = WebDriverWait(driver, 10).until( EC.presence_of_element_located((By.XPATH, '//*[@id="wrapperDiv"]/nav/ul'))) 
        count=driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > li').length;", parent)
        li_text=[]
        for _ in range(1,int(count)+1): 
            li_text.append(driver.find_element(By.XPATH, f'//*[@id="wrapperDiv"]/nav/ul/li[{_}]/a').text.split('\n')[0])
        driver.find_element(By.XPATH, '//*[@id="wrapperDiv"]/nav/ul/li[{}]/a'.format(li_text.index("리뷰")+1)).click()
        time.sleep(1)
        
        try:
                parent=driver.find_element(By.XPATH, '//*[@id="main"]/div[2]/div/div/div')
        except:
                parent=driver.find_element(By.XPATH, '//*[@id="main"]/div[3]/div/div/div')
        count = 0
        try:
            if driver.find_element(By.CSS_SELECTOR, '#main > div._7xsxe00 > label > div > span.mmxont2._1ltqxco1h.mmxont4').text=="블로그 리뷰": #자체 리뷰가 없을 경우
                driver.back()
                time.sleep(1)
                driver.back()
                reviews[restaurant].append('none')
                continue
        except:
            pass
        
        coment_count=driver.find_element(By.XPATH, '//*[@id="main"]/section[1]/div/div/div[1]/h5/span').text
        coment_count=coment_count.split('개')[0]
        if int(coment_count) > 24: #댓글이 24개 이상일 경우
            while count < 24: #댓글 로딩
                driver.execute_script("window.scrollBy(0, 100);")
                count=driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > div').length;", parent)
        else:
            while count < int(coment_count): #댓글 로딩
                driver.execute_script("window.scrollBy(0, 100);")
                count=driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > div').length;", parent)
        
        for j in range(1, count): #댓글 크롤링
            try:
                rating=driver.find_element(By.XPATH,'//*[@id="main"]/div[2]/div/div/div/div[{}]/article/div[1]/div[2]/div/a/div'.format(j)).text
                try:                                   
                    coment=driver.find_element(By.XPATH,'//*[@id="main"]/div[2]/div/div/div/div[{}]/article/div[2]/div[2]/p'.format(j)).text
                except:
                    coment=''
                    
            except:
                rating=driver.find_element(By.XPATH,'//*[@id="main"]/div[3]/div/div/div/div[{}]/article/div[1]/div[2]/div/a/div'.format(j)).text
                try:                             
                    coment=driver.find_element(By.XPATH,'//*[@id="main"]/div[3]/div/div/div/div[{}]/article/div[2]/div[2]/p'.format(j)).text
                except:
                    coment=''
    
           
            if len(coment.strip()) >= 10:
                reviews[restaurant].append((rating, coment))

        driver.back()
        time.sleep(1)
        driver.back()
        time.sleep(1)
        print(i)

        with open(f'reviews_CT_{location}.json', 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        print("✅ 캐치테이블 저장 완료")

    driver.quit()
    print("🛑 드라이버 종료 완료")


# 사용 예시:
# collect_data('naver', '서대문구')
collect_data('catchtable', '서대문구', ct_id='01067017382', ct_pw='xorehd123!')
