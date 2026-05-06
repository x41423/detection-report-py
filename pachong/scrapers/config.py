"""价格爬虫配置"""

BASE_URL = "http://price.cnveg.com"
MOBILE_URL = "http://m.cnveg.com/"

DEFAULT_VARIETIES = [
    "白菜",
    "西红柿",
    "黄瓜",
    "土豆",
    "青椒",
    "茄子",
    "芹菜",
    "菠菜",
    "生菜",
    "胡萝卜",
    "白萝卜",
    "洋葱",
    "大蒜",
    "生姜",
    "韭菜",
    "大葱",
    "蒜薹",
    "豆角",
    "莴笋",
    "油麦菜",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

REQUEST_DELAY = 1.0
