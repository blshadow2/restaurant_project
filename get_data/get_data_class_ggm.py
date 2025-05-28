import time
import json
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, JavascriptException
from selenium.webdriver.common.action_chains import ActionChains
from config import id,password



class BaseCrawler:
    """공통 웹드라이버 설정 및 유틸 메서드 제공 클래스."""
    def __init__(self, headless=True):
        opts = Options()
        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/114.0.0.0 Safari/537.36")
        opts.add_argument(f"user-agent={ua}")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("detach", True)
        if headless:
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")
        self.driver = webdriver.Chrome(options=opts)
    
    def scroll_to_bottom(self, container, step=1000, max_steps=30): #페이지를 끝까지 로드
        last_h = self.driver.execute_script("return arguments[0].scrollHeight;", container)
        for _ in range(max_steps):
            self.driver.execute_script("arguments[0].scrollTop += arguments[1];", container, step)
            time.sleep(1)
            new_h = (self.driver.execute_script("return arguments[0].scrollHeight;", container))
            if new_h == last_h:
                break
            last_h = new_h
    
    def scroll_into_view(self, el): #요소를 컨테이너 중간으로 로드
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    
    def click_tab(self, tab_name, container_locator): #탭에서 이름이 tab_name인 버튼을 클릭
        try:
            parent = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(container_locator)
            )
        except TimeoutException:
            return False
        for tab in parent.find_elements(By.XPATH, ".//a"):
            tab_text = tab.text.split('\n')[0]
            if tab_text == tab_name:
                tab.click()
                break
    
    def back_to_list(self): #list-target-reviews에서 list로
        self.driver.back(); time.sleep(0.5)
        self.driver.back(); time.sleep(0.5)
    
    def save_reviews(self, data, filename): #dictionary 데이터를 json으로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

# class CatchTableCrawler(BaseCrawler):
#     def __init__(self, user_id, user_pw, **kwargs):
#         super().__init__(**kwargs)
#         self.user_id = user_id
#         self.user_pw = user_pw
#         self.logged_in = False

#     def _login(self):
#         self.driver.get("https://app.catchtable.co.kr/ct/login")
#         time.sleep(2)
#         try:
#             self.driver.find_element(By.XPATH,
#                 '//*[@id="root"]/div[2]/main/section/div[2]/div/div/div/button[3]'
#             ).click()
#         except NoSuchElementException:
#             pass
#         time.sleep(1)
#         self.driver.find_element(By.ID, "login-id").send_keys(self.user_id)
#         pw = self.driver.find_element(By.ID, "login-pw")
#         pw.send_keys(self.user_pw); pw.send_keys(Keys.ENTER)
#         self.logged_in = True
#         time.sleep(2)


#     def crawl(self):
#         if not self.logged_in:
#             self._login()

#         time.sleep(1)
#         self.driver.find_element(By.XPATH, '//*[@id="popup"]/div/div/div/div/div[2]/button[1]').click()  
#         self.driver.find_element(By.XPATH, '//*[@id="root"]/div[3]/div/a').click()
#         #알림 제거
#         self.driver.find_element(By.XPATH, '//*[@id="header"]/div/form/input').click()
#         time.sleep(1)
#         self.driver.find_element(By.XPATH, '//*[@id="header"]/div/div/div/input').send_keys('서대문구')
#         time.sleep(1)
#         restaurant_count=self.driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div/div/div[1]/span').text
#         print(restaurant_count)
#         self.driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div').click()
#         time.sleep(3)
#         handle=self.driver.find_element(By.CSS_SELECTOR, '#status-bar-open-map > div > div.modal-location > div:nth-child(2) > div._53lcbm0._53lcbm2 > div.xnbnj35')
#         actions = ActionChains(self.driver)
#         actions.click_and_hold(handle)             \
#             .move_by_offset(0, -300)            \
#             .release()                          \
#             .perform()
#         time.sleep(3)
#         flag=0
#         reviews={}
#         for i in range(int(restaurant_count)):
#             target_restaurant=self.driver.find_element(By.XPATH, '//*[@id="virtual_{}"]'.format(i))
#             restaurant_name=self.driver.find_element(By.XPATH, '//*[@id="virtual_{}"]/div/div/div[1]/div/div/div[1]/div[1]/p'.format(i)).text
#             total_reviews_count=self.driver.find_elements(By.CSS_SELECTOR, f'#virtual_{i} > div > div > div.ShopListItem_topInfoBox__1p45wh61 > div > div > div.ShopListItem_infoBox__1p45wh63 > div.ShopHeaderInfo_box__1lnb8ff0 > div')
#             print(restaurant_name)
#             reviews[restaurant_name]=[]
#             if not total_reviews_count: # 리뷰가 없는 경우 다음으로
#                 reviews[restaurant_name].append('none')
#                 continue
#             try: # 음식점 페이지 진입 & 특정 항목에 처음 진입시 팝업해결
#                 elems=self.driver.find_element(By.XPATH, '//*[@id="virtual_{}"]/div/div/div[1]/div/div[1]/div/div/div/button/span'.format(i))
#             except:
#                 elems=False
#             if elems: 
#                 if elems.text =="위스키 페어링 맛집" and flag==0:
#                     self.scroll_into_view(target_restaurant)
#                     time.sleep(0.3)  # 렌더링 안정화
#                     target_restaurant.click()
#                     time.sleep(1)
#                     self.driver.find_element(By.XPATH, '//*[@id="popup"]/div/div/div/div/div/button[1]').click()
#                     flag=1
#                 else:
#                     self.scroll_into_view(target_restaurant)
#                     time.sleep(0.3)  # 렌더링 안정화
#                     target_restaurant.click()  
#             else:        
#                 self.scroll_into_view(target_restaurant)
#                 time.sleep(0.3)  # 렌더링 안정화
#                 target_restaurant.click()
            
#             time.sleep(2)
#             #리뷰창 진입
#             try:
#                 self.driver.find_element(By.XPATH,'/html/body/div[4]/div/div/div/button[1]').click()
#             except:
#                 pass
#             parent = (By.XPATH, '//*[@id="wrapperDiv"]/nav/ul')
#             self.click_tab("리뷰", parent)
#             time.sleep(1)
            
#             try:
#                 if self.driver.find_element(By.CSS_SELECTOR, '#main > div._7xsxe00 > label > div > span.mmxont2._1ltqxco1h.mmxont4').text=="블로그 리뷰": #자체 리뷰가 없을 경우
#                     self.back_to_list()
#                     reviews[restaurant_name].append('none')
#                     continue
#             except:
#                 pass

#             try:
#                     comment_wrap=self.driver.find_element(By.XPATH, '//*[@id="main"]/div[2]/div/div/div')
#             except:
#                     comment_wrap=self.driver.find_element(By.XPATH, '//*[@id="main"]/div[3]/div/div/div')
#             count = 0
#             coment_count=self.driver.find_element(By.XPATH, '//*[@id="main"]/section[1]/div/div/div[1]/h5/span').text
#             coment_count=coment_count.split('개')[0].replace(',','')
#             if int(coment_count) > 24: #댓글이 24개 이상일 경우
#                 while count < 24: #댓글 로딩
#                     self.driver.execute_script("window.scrollBy(0, 100);")
#                     count=self.driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > div').length;", comment_wrap)
#             else:
#                 while count < int(coment_count): #댓글 로딩
#                     self.driver.execute_script("window.scrollBy(0, 100);")
#                     count=self.driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > div').length;", comment_wrap)
            
#             for j in range(1, count): #댓글 크롤링 
#                 rating=comment_wrap.find_element(By.XPATH,'.//div[{}]/article/div[1]/div[2]/div/a/div'.format(j)).text
#                 try:                             
#                     coment=comment_wrap.find_element(By.XPATH,'.//div[{}]/article/div[2]/div[2]/p'.format(j)).text
#                 except:
#                     coment=''
#                 reviews[restaurant_name].append((rating,coment))
#             self.back_to_list()
#             self.save_reviews(reviews, 'reviews_ct.json')

# class NaverMapCrawler(BaseCrawler):
#     def crawl(self):
#         self.driver.get("https://map.naver.com/p/search/%EC%84%9C%EB%8C%80%EB%AC%B8%EA%B5%AC%20%EB%A7%9B%EC%A7%91?c=13.00,0,0,0,dh")
#         time.sleep(3)
#         search=self.driver.find_element(By.CLASS_NAME,'input_search')
#         search.click()
#         search.send_keys(Keys.ENTER)
#         time.sleep(3)
#         search_frame=self.driver.find_element(By.ID, 'searchIframe')
#         self.driver.switch_to.frame(search_frame)
#         scrollable_element=self.driver.find_element(By.XPATH, '//*[@id="_pcmap_list_scroll_container"]') 
#         self.scroll_to_bottom(scrollable_element)
#         for j in range(2,4):
#             if j>2:
#                 self.driver.find_element(By.XPATH, f'//*[@id="app-root"]/div/div[2]/div[2]/a[{j}]').click()
#             reviews={}
#             time.sleep(3)
#             restaurants=self.driver.find_elements(By.CSS_SELECTOR, 'li[data-laim-exp-id="undefinedundefined"]')
#             for li in restaurants:
#             # 예: li 내부의 div > a > div > div > span 모두 가져오기 (XPath)
#                 span_restaurants = li.find_elements(By.XPATH, ".//div[1]/div[1]/a/span[contains(@class, 'TYaxT')]")
#                 span_category = li.find_elements(By.XPATH, ".//div[1]/div[1]/a/span[contains(@class, 'KCMnt')]")
#                 button=li.find_element(By.XPATH, ".//div[1]/div[1]/a")
#                 for name in span_restaurants:
#                     for category in span_category:
#                         print(name.text, category.text)
#                         reviews[name.text]={}
#                         reviews[name.text]['category']=category.text
#                         restaurant_name=name.text
#                         button.click()
#                         time.sleep(2)
#                         self.driver.switch_to.default_content()
#                         self.driver.switch_to.frame(self.driver.find_element(By.ID, 'entryIframe'))
#                         try:
#                             error=self.driver.find_element(By.CLASS_NAME,'vEAWt')
#                             if error:
#                                 self.driver.switch_to.default_content()
#                                 self.driver.switch_to.frame(search_frame)
#                                 button.click()
#                         except:
#                             pass
#                         parent = WebDriverWait(self.driver, 10).until( EC.presence_of_element_located((By.XPATH, '//*[@id="app-root"]/div/div/div/div[4]/div/div/div/div')))
#                         restaurant_address=self.driver.find_element(By.CSS_SELECTOR,'span.LDgIH').text
#                         reviews[restaurant_name]['address']=restaurant_address
#                         self.click_tab("리뷰",(By.XPATH, '//*[@id="app-root"]/div/div/div/div[4]/div/div/div/div'))
#                         comments=[]
#                         flag=0
#                         while flag==0:
#                             try:
#                                 self.driver.execute_script("window.scrollBy(0, 1500);")
#                                 comment=WebDriverWait(self.driver, 20).until( EC.presence_of_element_located((By.XPATH, '//*[@id="_review_list"]/li[1]/div[5]/a[1]'))).text
#                             except TimeoutException:
#                                 self.click_tab("리뷰",(By.XPATH, '//*[@id="app-root"]/div/div/div/div[4]/div/div/div/div'))
#                                 continue
#                             except:
#                                 continue
#                             flag=1
#                         comment_list=self.driver.find_element(By.XPATH,'//*[@id="_review_list"]')
#                         comments.append(comment)
#                         comment_count=self.driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > li').length;", comment_list)
#                         for i in range(2,comment_count+1):
#                             self.driver.execute_script("window.scrollBy(0, 1500);")
#                             comment=self.driver.find_element(By.XPATH, '//*[@id="_review_list"]/li[{}]/div[5]/a[1]'.format(i)).text
#                             comments.append(comment)
                        
#                         reviews[restaurant_name]['comment']=comments
#                     self.driver.switch_to.default_content()
#                     self.driver.switch_to.frame(search_frame)
#             if j==2:
#                 self.save_reviews(reviews,"reviews_NM.json")
#             else:
#                 with open('reviews_NM.json', 'r', encoding='utf-8') as f:
#                     data = json.load(f)
#                 data.update(reviews)
#                 self.save_reviews(data,"reviews_NM.json")

# class KakaoMapCrawler(BaseCrawler):
#     def crawl(self):
#         self.driver.get('https://map.kakao.com/')
#         self.driver.find_element(By.XPATH,'//*[@id="search.keyword.query"]').send_keys('서대문구 맛집'+Keys.ENTER)
#         WebDriverWait(self.driver,10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="info.search.place.list"]/li[1]/div[5]/div[4]/a[1]')))
#         reviews={}
#         for i in range(1,6):
#             if i>2:
#                 button=self.driver.find_element(By.XPATH,f'//*[@id="info.search.page.no{i}"]')
#                 button.send_keys(Keys.ENTER)
#             for j in range(1,16):
#                 print(i,j)
#                 restaurant=self.driver.find_element(By.XPATH,'//*[@id="info.search.place.list"]/li[{}]/div[3]/strong/a[2]'.format(j)).text
#                 link=self.driver.find_element(By.XPATH, '//*[@id="info.search.place.list"]/li[{}]/div[5]/div[4]/a[1]'.format(j)).get_attribute("href")
#                 self.driver.get(link)
#                 parent=WebDriverWait(self.driver,10).until(EC.presence_of_element_located((By.XPATH,'//*[@id="mainContent"]/div[2]/div[1]/div/ul')))
#                 count=self.driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > li').length;", parent)
#                 li_text=[]
#                 for _ in range(1,int(count)+1):
#                     li_text.append(self.driver.find_element(By.XPATH, f'//*[@id="mainContent"]/div[2]/div[1]/div/ul/li[{_}]/a').text.split('\n')[0])
#                 if "후기" not in li_text:
#                     self.driver.back()
#                     reviews[restaurant]='none'
#                     continue
#                 self.driver.find_element(By.XPATH, '//*[@id="mainContent"]/div[2]/div[1]/div/ul/li[{}]/a'.format(li_text.index("후기")+1)).click()
#                 parent=WebDriverWait(self.driver,10).until(EC.presence_of_element_located((By.XPATH,'//*[@id="mainContent"]/div[2]/div[2]/div[2]/div[3]/ul')))
#                 count=self.driver.execute_script("const parent = arguments[0];return parent.querySelectorAll(':scope > li').length;", parent)
#                 comments=[]
#                 for k in range(1,int(count)+1):
#                     try:
#                         comment=self.driver.find_element(By.XPATH,f'//*[@id="mainContent"]/div[2]/div[2]/div[2]/div[3]/ul/li[{k}]/div/div[2]/div/div[1]/div[2]/a/p').text
#                     except:
#                         comment=''
#                     comments.append(comment)
#                 reviews[restaurant]=comments
#                 self.back_to_list()
#             time.sleep(2)
#             if i==1:
#                 more=self.driver.find_element(By.XPATH,'//*[@id="info.search.place.more"]')
#                 more.send_keys(Keys.ENTER)
#                 time.sleep(3)
#         self.save_reviews(reviews,'reviews_KM.json')

class GoogleMapCrawler(BaseCrawler):
    def crawl(self):
        self.driver.get("https://www.google.com/maps")
        time.sleep(1)

        try:
            search_box = self.driver.find_element(By.ID, "searchboxinput")
            search_box.send_keys("서대문구 맛집")
            search_box.send_keys(Keys.ENTER)
        except Exception as e:
            print(f"[검색창 오류] {e}")
            return
        time.sleep(3)

        try:
            scrollable_area = self.driver.find_element(By.XPATH, '//div[contains(@aria-label, "결과") and @role="feed"]')
        except NoSuchElementException:
            print("[스크롤 영역 오류]")
            return

        prev_count = 0
        scrolls = 0
        max_scrolls = 35
        same_count = 0
        same_count_limit = 5

        while scrolls < max_scrolls and same_count < same_count_limit:
            try:
                self.driver.execute_script("arguments[0].scrollBy(0, 800);", scrollable_area)
                time.sleep(1)

                items = self.driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK')
                if len(items) == prev_count:
                    same_count += 1
                else:
                    same_count = 0
                    prev_count = len(items)

                scrolls += 1
            except (StaleElementReferenceException, JavascriptException) as e:
                print(f"[스크롤 오류] {e}")
                break

        try:
            listings = self.driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK')
            print(f"총 수집된 식당 수: {len(listings)}")
        except Exception as e:
            print(f"[목록 수집 실패] {e}")
            return

        results = []

        for idx, listing in enumerate(listings):
            try:
                name = ""
                rating = ""
                reviews = ""
                link = ""

                try:
                    name = listing.find_element(By.CSS_SELECTOR, '.qBF1Pd').text
                except:
                    name = "이름없음"

                try:
                    rating = listing.find_element(By.CSS_SELECTOR, 'span.MW4etd').text
                except:
                    rating = "0.0"

                try:
                    reviews = listing.find_element(By.CSS_SELECTOR, 'span.UY7F9').text
                except:
                    reviews = "리뷰 없음"

                try:
                    link_elem = listing.find_element(By.CSS_SELECTOR, 'a.hfpxzc')
                    link = link_elem.get_attribute("href")
                except:
                    link = "링크 없음"

                print(f"[{idx+1}] {name} / 평점: {rating} / 리뷰: {reviews} / 링크: {link}")

                results.append({
                    "name": name,
                    "rating": rating,
                    "reviews": reviews,
                    "link": link
                })

            except Exception as e:
                print(f"[{idx+1}] 항목 처리 오류: {e}")
                continue

        # 저장
        with open("reviews_GM.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("저장 완료: reviews_GM.json") 

if __name__ == "__main__":
    # 작업 디렉터리: 이 스크립트가 있는 폴더
    os.chdir(os.path.dirname(__file__))

    # 캐치테이블: 아이디/비밀번호 입력
    # CT_ID = id
    # CT_PW = password
    # ct = CatchTableCrawler(CT_ID, CT_PW, headless=False)
    # ct.crawl()
    # ct.driver.quit()

    # nm = NaverMapCrawler()
    # nm.crawl()
    # nm.driver.quit()

    # km = KakaoMapCrawler()
    # km.crawl()
    # km.driver.quit()

    gm = GoogleMapCrawler()
    gm.crawl()
    gm.driver.quit()
