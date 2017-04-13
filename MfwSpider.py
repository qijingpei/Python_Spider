'''
目标：爬取蚂蜂窝
获取热门城市 -> 获取城市下的游记列表 -> 获取游记内容 -> 提取游记内容的游记标题、城市、出发时间等，
接下来我们用三个步骤来实现它。。。
'''
import re
import requests
from pyquery import PyQuery as pq#用一个简单的名字
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from Travel.config import *
import time
from requests.exceptions import RequestException
from multiprocessing import Pool#multi processing


browser = webdriver.PhantomJS(service_args=SERVICE_ARGS)#PhantomJS可以模拟浏览器，而且不用弹出浏览器
wait = WebDriverWait(browser, 10)
browser.set_window_size(1400, 900)#设置一下窗口大小，如果太小会影响效果

def get_one_page(url):#获得一个页面的html代码
    try:
        response = requests.get(url)
        if response.status_code == 200:
             return response.text
        return None
    except RequestException:
        return None

def get_total_city_pages():#获取城市列表总页数，成功
    print('获取城市列表总页数')
    #用phantomJS来写的，其实用requests来写也一样！~
    try:
        browser.get('http://www.mafengwo.cn/mdd/citylist/21536.html')
        total = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR,'#citylistpagination > div > span.count'))#等到总页数出现
        )
        return total.text
    except TimeoutException:
        return get_total_city_pages()#递归，until there is result to return

def get_cities_info(page_number):#通过在url中输入页数，跳转到其他页面
    #try:
    url = 'http://www.mafengwo.cn/mdd/citylist/21536.html?mddid=21536&page=' + str(page_number)
    html = get_one_page(url)#获得网页的html代码
    #print(html)
    pattern = re.compile(r'class="item ".*?href="(.*?)".*?title">(.*?)<p.*?<b>(.*?)</b>.*?</li>', re.S)
    items =re.findall(pattern, html)
    for item in items:
        #print('正在获取城市信息')
        city = {
            'url': 'http://www.mafengwo.cn/' + item[0].strip(),
            'name': item[1].strip(),  # 城市名字
            'number': item[2]  # 人数
        }
        print(city)
        #print(city.get('url'))
        get_city_strategies(city.get('url'))#获取一个城市的所有攻略
    '''#except Exception:
        print('重新获取城市信息')
        print(Exception)
        get_cities_info(page_number)
    '''
def get_strategy_total_page(url):#获取一个城市的所有攻略的总页数
    index = re.search(r'mafengwo/(\d*?).html',url)#获取一个城市的标识
    print('index:'+index.group(1))
    #凑出攻略列表界面的类型：http://www.mafengwo.cn/yj/10189/1-0-1.html'，10189是城市标识，1-0-1中最后1个1是攻略列表页面的标识，通过修改他们俩获得所有攻略
    str_url = 'http://www.mafengwo.cn/yj/' + index.group(1) +'/1-0-1.html'#攻略列表的url
    r = requests.get(str_url)
    html = r.text
    #print('攻略界面：'+html)
    pattern = re.compile(r'class="count">共<span>(.*?)</span>页')
    total = re.search(pattern, html)
    if total :
        print('攻略总页数：'+total.group(1))#获取攻略总页数，这里的“.group(1)”会从中提取出页数（其实我也不明白是怎么提取出来的）
        return total.group(1)
    return get_strategy_total_page(url)

def get_city_strategies(url):#获取一个城市的所有攻略
    total = int(get_strategy_total_page(url))#总页数
    index = re.search(r'mafengwo/(\d*?).html', url)  # 获取一个城市的标识
    #print('index:' + index.group(1))
    # 凑出攻略列表界面的类型：http://www.mafengwo.cn/yj/10189/1-0-1.html'，10189是城市标识，1-0-1中最后1个1是攻略列表页面的标识，通过修改他们俩获得所有攻略
    for i in range(1, 2):#左闭右开
        str_list_url = 'http://www.mafengwo.cn/yj/' + index.group(1) + '/1-0-'+str(i)+'.html'  # 攻略strategy列表的url
        print('攻略列表的url：'+str_list_url)
        #--------解析出每个攻略列表页面的多个攻略url：
        parse_strategies_list(str_list_url)
        #对每一个攻略的url进行访问，得到出发时间等信息，存到数据库中：
        #get_strategies_info(str_list_url)

def parse_strategies_list(url):#--------解析出每个攻略列表页面的多个攻略url：
    #url = 'http://www.mafengwo.cn/yj/10065/1-0-1.html' #测试用的用例
    r = requests.get(url)
    html = r.text
    #print(html)
    # 网页中攻略的网址：href="/i/6536459.html"  ，匹配之
    pattern = re.compile(r'href="(/i/.*?.html)"\s{1}target="_blank">[\s\S]*?</h2>')
    # \s:表示空白字符，\s{1}：表示1个空格
    items = re.findall(pattern, html)
    if items:
        for item in items:
            item = 'http://www.mafengwo.cn' + item
            print(item)
            parse_one_strategy(item)#解析这个攻略的url

def parse_one_strategy(url):#对每一个攻略的url进行解析，得到出发时间等信息，存到数据库中：
    #url = 'http://www.mafengwo.cn/i/2996543.html'
    print('一个攻略的url:'+url)
    r = requests.get(url)
    r.encoding = r.apparent_encoding
    html = r.text
    #print(html)
    #-------处理第一种攻略：有“出发时间”的攻略
    pattern1 = re.compile(r'出发时间<span>/</span>(\d*?)-(\d*?)-(\d*?)<i></i>')
    result = re.search(pattern1, html)
    if result:
        time = {
            'year': result.group(1),
            'month':result.group(2),
            'day':result.group(3),
        }
        print('获取到攻略的出发时间：'+result.group(1)+result.group(2)+result.group(3))
        #存储到数据库
    else:#-------处理第二种攻略：没有“出发时间”的攻略(还没有完成！！！)
        print('没有获取到攻略的出发时间')
        return

def main():
    #try:
    total = get_total_city_pages()
    total = int(re.compile('(\d+)').search(total).group(1))##从“共400页”中获取总页数，强转成int型
    print(total)
    pool = Pool()
    pool.map(get_cities_info, [1])#Apply `func` to each element in `iterable`(即第二个参数),
    #————————注意每个城市现在只爬取了1页！！！————————
    # (1页有9个城市，9页*15个攻略耗费时间：625.2638635008296=10min) (没有获取到的有45个，获取到的有90个)
    #get_cities_info(1)
    #for i in range(1, 10):
    #    get_cities_info(i)
    '''
    #except Exception:
        print('出错啦')
    #finally:
        browser.close()
    '''

if __name__ == '__main__':
    start = time.clock()
    main()
    end = time.clock()
    print('耗费时间：'+str(end-start))#4.249068744382217s
















