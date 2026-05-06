# BloginfoSpider.py （基于A版本，动态读取配置）
import scrapy
import json
import re
import sys
import os

sys.path.insert(0, r'D:\BYSJ\djangop8gh5erc')
os.chdir(r'D:\BYSJ\djangop8gh5erc')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dj2.settings')
import django
django.setup()

from main.config_model import config
from main.models import bloginfo
from ..items import BloginfoItem


def extract_uid_from_url(userurl):
    if not userurl:
        return None
    match = re.search(r'(?:weibo\.com/|/u/)(\d+)', userurl)
    return match.group(1) if match else None


class BloginfoSpider(scrapy.Spider):
    name = 'bloginfoSpider'
    custom_settings = {
        'HTTPERROR_ALLOWED_CODES': [400, 403],
        'RETRY_HTTP_CODES': [500, 503],
        'DOWNLOAD_DELAY': 5,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def start_requests(self):
        # 1. 从数据库读取 Headers
        headers = {}
        try:
            obj = config.objects.filter(name='weibo_request_headers').first()
            if obj and obj.value:
                headers = json.loads(obj.value)
        except:
            pass

        # 2. 从数据库读取 Cookie 并解析
        cookies = {}
        try:
            obj = config.objects.filter(name='weibo_full_cookie').first()
            if obj and obj.value:
                cookie_str = obj.value.strip()
                for part in cookie_str.split(';'):
                    part = part.strip()
                    if '=' in part:
                        k, v = part.split('=', 1)
                        cookies[k.strip()] = v.strip()
        except:
            pass

        # 3. 获取要爬取的博主UID列表
        uids = []
        try:
            from main.models import SeedBlogger
            seed_uids = SeedBlogger.objects.values_list('uid', flat=True).distinct()
            uids = [str(uid) for uid in seed_uids]
        except:
            uids = []

        if not uids:
            bloggers = bloginfo.objects.exclude(userurl__isnull=True).exclude(userurl='').values('userurl').distinct()
            for b in bloggers:
                uid = extract_uid_from_url(b['userurl'])
                if uid and uid not in uids:
                    uids.append(uid)

        # 4. 发起请求
        if not uids:
            # 回退到搜索接口
            for page in range(1, 10):
                url = f'https://m.weibo.cn/api/container/getIndex?containerid=100103type=1&q=社交媒体&page={page}'
                yield scrapy.Request(url=url, callback=self.parse, headers=headers, cookies=cookies)
        else:
            for uid in uids:
                for page in range(1, 6):
                    url = f'https://m.weibo.cn/api/container/getIndex?containerid=107603{uid}&page={page}'
                    yield scrapy.Request(url=url, callback=self.parse, headers=headers, cookies=cookies)

    def parse(self, response):
        try:
            data = json.loads(response.text)
        except:
            return

        cards = data.get('data', {}).get('cards', [])
        for card in cards:
            mblog = card.get('mblog')
            if not mblog:
                continue

            fields = BloginfoItem()
            try:
                fields['screenname'] = mblog['user']['screen_name']
            except:
                pass
            try:
                fields['mblogtext'] = mblog.get('text', '')
            except:
                pass
            try:
                fields['commentscount'] = int(mblog.get('comments_count', 0))
            except:
                pass
            try:
                fields['attitudescount'] = int(mblog.get('attitudes_count', 0))
            except:
                pass
            try:
                fields['repostscount'] = int(mblog.get('reposts_count', 0))
            except:
                pass
            try:
                fields['fbtime'] = mblog.get('created_at', '')
            except:
                pass
            try:
                fields['medias'] = mblog.get('source', '')
            except:
                pass
            try:
                uid = mblog['user']['id']
                fields['userurl'] = f'https://weibo.com/{uid}'
            except:
                pass
            try:
                fields['weibo_id'] = int(mblog['id'])
            except:
                pass

            yield fields