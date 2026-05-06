# 管道文件

import pymysql
import pymssql
from itemadapter import ItemAdapter

class SpiderPipeline(object):

    # 打开数据库
    def open_spider(self, spider):
        type = spider.settings.get('TYPE', 'mysql')
        host = spider.settings.get('HOST', 'localhost')
        port = int(spider.settings.get('PORT', 3306))
        user = spider.settings.get('USER', 'root')
        password = spider.settings.get('PASSWORD', '123456')

        try:
            database = spider.databaseName
        except:
            database = spider.settings.get('DATABASE', '')

        if type == 'mysql':
            self.connect = pymysql.connect(host=host, port=port, db=database, user=user, passwd=password, charset='utf8mb4')
        else:
            self.connect = pymssql.connect(host=host, user=user, password=password, database=database)
            
        self.cursor = self.connect.cursor()

    # 关闭数据库
    def close_spider(self, spider):
        self.connect.close()

    # 对数据进行处理
    def process_item(self, item, spider):
        self.insert_db(item, spider.name)
        return item



    # 插入数据
    def insert_db(self, item, spiderName):
        values = tuple(item.values())
        # print(values)

        qmarks = ', '.join(['%s'] * len(item))
        cols = ', '.join(item.keys())

        sql = "INSERT IGNORE INTO %s (%s) VALUES (%s)" % (spiderName.replace('Spider', ''), cols, qmarks)

        self.cursor.execute(sql, values)
        self.connect.commit()


class BloggerProfilePipeline:
    def process_item(self, item, spider):
        if spider.name != 'bloggerProfileSpider':
            return item

        import sys, os

        # --- 关键：添加 Django 项目根目录到 sys.path ---
        # 路径是你的 Django 项目根目录（包含 manage.py 的目录）
        django_project_path = r'D:\BYSJ\djangop8gh5erc'
        if django_project_path not in sys.path:
            sys.path.insert(0, django_project_path)

        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dj2.settings')

        import django
        django.setup()
        # ---------------------------------------------

        from main.models import blogger_profile

        blogger_profile.objects.update_or_create(
            screenname=item['screenname'],
            defaults={
                'followers_count': item.get('followers_count', 0),
                'friends_count': item.get('friends_count', 0),
                'statuses_count': item.get('statuses_count', 0),
                'verified': item.get('verified', 0),
                'verified_reason': item.get('verified_reason', '')
            }
        )
        return item