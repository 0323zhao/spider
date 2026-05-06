# BlogcommentSpider.py （最终稳定版：一次性入队、容错提取、翻页优化）
import json
import sys
import os
import scrapy

# ---------- Django 初始化 ----------
sys.path.insert(0, r'D:\BYSJ\djangop8gh5erc')
os.chdir(r'D:\BYSJ\djangop8gh5erc')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dj2.settings')
import django
django.setup()

from main.config_model import config
from main.models import bloginfo
from ..items import BlogcommentItem


class BlogcommentSpider(scrapy.Spider):
    name = 'blogcommentSpider'
    custom_settings = {
        'HTTPERROR_ALLOWED_CODES': [400, 403],
        'RETRY_HTTP_CODES': [500, 503],
        'DOWNLOAD_DELAY': 2.0,            # 请求间隔，可适当加大
        'CONCURRENT_REQUESTS': 1,         # 保持单线程，避免触发风控
    }

    # ---------- 可调参数 ----------
    TARGET_PER_POST = 30          # 每条博文最多抓取的评论数
    MAX_PAGES_PER_POST = 10       # 每条博文的最大翻页数（防止无限翻页）

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

        # 3. 保存为实例属性，供翻页复用
        self._headers = headers
        self._cookies = cookies

        # 4. 获取所有待抓取的博文 ID
        weibo_ids = bloginfo.objects.exclude(weibo_id__isnull=True).values_list('weibo_id', flat=True).distinct()
        ids = list(weibo_ids)

        if not ids:
            self.logger.error('暂无博文ID，请先运行 bloginfoSpider')
            return

        # 5. 【核心修复】一次性将所有博文的第一页请求全部入队，由引擎自动调度
        for mid in ids:
            yield self._make_request(mid, page=1, collected=0)

    def _make_request(self, blog_id, page, max_id=0, collected=0):
        """构造评论请求（内部工具方法）"""
        base_url = f'https://m.weibo.cn/comments/hotflow?id={blog_id}&mid={blog_id}'
        if max_id:
            url = f'{base_url}&max_id={max_id}&max_id_type=0'
        else:
            url = f'{base_url}&max_id_type=0'

        return scrapy.Request(
            url=url,
            callback=self.parse_page,
            headers=self._headers,
            cookies=self._cookies,
            meta={
                'blog_id': blog_id,
                'page': page,
                'max_id': max_id,
                'collected': collected,
                'target': self.TARGET_PER_POST,
                'max_page': self.MAX_PAGES_PER_POST,
            }
        )

    def parse_page(self, response):
        """解析单页评论，自动翻页或结束"""
        meta = response.meta
        blog_id = meta['blog_id']
        page = meta.get('page', 1)
        collected = meta.get('collected', 0)
        target = meta.get('target', self.TARGET_PER_POST)
        max_page = meta.get('max_page', self.MAX_PAGES_PER_POST)

        try:
            data = json.loads(response.text)
        except:
            self.logger.error(f'博文 {blog_id} 返回非 JSON，终止')
            return

        # 触发验证码或权限错误，直接终止该博文
        if data.get('ok') == -100:
            self.logger.error(f'博文 {blog_id} 请求被拦截（ok=-100），终止')
            return

        comments = data.get('data', {}).get('data', [])
        new_count = 0
        for comment in comments:
            fields = BlogcommentItem()
            #  -------------- 数据提取容错优化 --------------
            user_info = comment.get('user', {})
            fields['pluser'] = user_info.get('screen_name', '未知用户') if isinstance(user_info, dict) else '未知用户'
            fields['plcontent'] = (comment.get('text') or '').strip()
            fields['fbplace'] = (comment.get('source') or '').replace('来自 ', '') or '未知来源'
            fields['likecount'] = int(comment.get('like_count', 0))
            fields['pltime'] = comment.get('created_at', '未知时间')
            fields['detailurl'] = ''
            fields['blog_id'] = blog_id
            yield fields
            new_count += 1

        collected += new_count
        self.logger.info(f'博文 {blog_id} 第{page}页抓取 {new_count} 条，累计 {collected}/{target}')

        #  -------------- 翻页逻辑优化 --------------
        should_continue = (
            collected < target and          # 还没达到目标条数
            new_count > 0 and               # 当前页有数据
            page < max_page                 # 未超过翻页上限
        )

        next_max_id = data.get('data', {}).get('max_id', 0)
        has_next_page = (
            next_max_id is not None and
            str(next_max_id).strip() not in ('', '0')
        )

        if should_continue and has_next_page:
            next_page = page + 1
            yield self._make_request(
                blog_id,
                page=next_page,
                max_id=str(next_max_id),
                collected=collected
            )
        # 本条博文处理结束，引擎会自动处理队列中的下一条博文