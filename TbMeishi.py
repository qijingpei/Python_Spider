import re

import pymongo
from pyquery import PyQuery as pq#用一个简单的名字
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import requests
MONGO_URL = 'localhost'
MONGO_DB = 'taobao'
MONGO_TABLE = 'product'
KEYWORD = '美食'
#开启MongoDB
client = pymongo.MongoClient(MONGO_URL)
db=client[MONGO_DB]
SERVICE_ARGS = ['--load-images=false','--disk-cache=true']#不加载图片,开启缓存

browser = webdriver.PhantomJS(service_args=SERVICE_ARGS)#配置写在配置文件中了
wait = WebDriverWait(browser, 10)#下面要多次用到，先存一下，10表示等待时间

browser.set_window_size(1400 ,900)#设置一下窗口大小，如果太小会影响效果
def search():#按照关键词进行搜索
    print('正在搜索')
    try:
        browser.get('https://www.taobao.com')
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#q"))#等待搜索框出现，通过判断搜索框的CSS 选择器是否存在
        )
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button')))#
        # #J_SearchForm > button是从网页上复制的select，这个语句是要等到按钮可以被点击
        input.send_keys(KEYWORD)  #  在搜索框中输入要搜索的内容
        submit.click()
        total = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total')))#等到总页数出现
        get_products()#获取商品的信息
        return total.text
    except TimeoutException:
        return search()#递归，until there is result to return

def next_page(page_number):#通过输入页数，跳转到其他页面
    print('正在翻页',page_number)
    try:
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input'))
        )
        submit = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit')))
        input.clear()#清空内容
        input .send_keys(page_number)
        submit.click()
        #判断传入的页数是否是高亮，即判断是否跳转到了正确的页数
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'),str(page_number)))#判断是否是这个页数
        get_products()#获取商品的信息
    except TimeoutException:
        next_page(page_number)

def get_products():#获取商品的信息
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-itemlist .items .item')))
    html = browser.page_source#拿到网页的源代码
    doc = pq(html)#用pyquery解析源代码，pyquery对解析jquery、html比较好用
    items = doc('#mainsrp-itemlist .items .item').items()#得到所有的item
    for item in items:
        product = {
            'image': item.find('.pic .img').attr('src'),
            'price': item.find('.price').text(),
            'deal' : item.find('.deal-cnt').text()[:-3],
            'title' :item.find('.J_ClickStat').text(),
            'shop' : item.find('.shop').text(),
            'location' : item.find('.location').text()
        }
        print(product)
        #save_to_mongo(product)
'''
def save_to_mongo(result):
    try:
        if db[MONGO_TABLE].insert(result):
            print('存储到MONGODB成功',result)
    except Exception:
        print('存储到MONGODB失败', result)
'''
def main():
    try:
        total = search()
        total = int(re.compile('(\d+)').search(total).group(1))#从“共100页”中获取总页数，强转成int型
        for i in range(2, total + 1):#从2开始（1已经在search()中访问过了），到total（总页数），这里也应该是个左闭右开包
            next_page(i)
    except Exception:
        print('出错啦')
    finally:
        browser.close()
if __name__ == '__main__':
    main()



