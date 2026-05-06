# 数据容器文件

import scrapy

class SpiderItem(scrapy.Item):
    pass

class BloginfoItem(scrapy.Item):
    # 博主
    screenname = scrapy.Field()
    # 博文
    mblogtext = scrapy.Field()
    # 评论数
    commentscount = scrapy.Field()
    # 点赞数
    attitudescount = scrapy.Field()
    # 转发数
    repostscount = scrapy.Field()
    # 发布时间
    fbtime = scrapy.Field()
    # 媒体
    medias = scrapy.Field()
    # 主页地址
    userurl = scrapy.Field()

    weibo_id = scrapy.Field()

class BlogcommentItem(scrapy.Item):
    # 评论人
    pluser = scrapy.Field()
    # 评论内容
    plcontent = scrapy.Field()
    # 发布地
    fbplace = scrapy.Field()
    # 支持数
    likecount = scrapy.Field()
    # 评论时间
    pltime = scrapy.Field()
    # 详情地址
    detailurl = scrapy.Field()

    blog_id = scrapy.Field()

class BloggerProfileItem(scrapy.Item):
    screenname = scrapy.Field()
    followers_count = scrapy.Field()
    friends_count = scrapy.Field()
    statuses_count = scrapy.Field()
    verified = scrapy.Field()
    verified_reason = scrapy.Field()


