from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.core.cache import cache
from django.core.paginator import Paginator
from apps.goods.models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsImage
from django_redis import get_redis_connection
from apps.order.models import OrderGoods
# Create your views here.

# class Test(object):
#     def __init__(self):
#         self.name = 'abc'
# t = Test()
# t.age = 10
# print(t.age)

#127.0.0.1:8000/index
class IndexView(View):
    '''首页'''
    def get(self, request):
        '''显示首页'''
        #查看是否有缓存
        context = cache.get('index_page_data')

        if context is None:
            print('设置缓存')
            #获取商品的种类信息
            types = GoodsType.objects.all()

            #获取首页轮播商品信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            #获取首页促销活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            #获取首页分类商品展示信息
            for type in types: #GoodsType
                # 获取type种类首页分类商品的图片展示信息
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                # 获取type种类首页分类商品的文字展示信息
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

                #动态给type添加属性，分别保存首页分类商品的图片展示信息和文字展示信息
                type.image_banners = image_banners
                type.title_banners = title_banners

            #组织模板上下文
            context = {
                'types':types,
                'goods_banners':goods_banners,
                'promotion_banners':promotion_banners,
            }

            #设置缓存
            #kye value timeout
            cache.set('index_page_data', context, 3600)

        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            #用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)


        context.update(cart_count=cart_count)

        #使用模板
        return render(request, 'index.html', context)

#/goods/detail/id
class DetailView(View):
    '''详情页'''
    def get(self, request, goods_id):
        '''显示详情页'''
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            #商品不存在
            return redirect(reverse('goods:index'))

        #获取商品的分类信息
        types = GoodsType.objects.all()

        #获取商品的评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        #获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        #获取相同SPU的其他规格的产品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            #用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)

            #保存用户浏览记录
            conn = get_redis_connection('default')
            history_key = 'history_%d'%user.id
            #删除列表中的goods_id
            conn.lrem(history_key, 0, goods_id)
            #将浏览的商品id插入redis数据库左侧
            conn.lpush(history_key, goods_id)
            #只保留用户最新浏览的5条数据
            conn.ltrim(history_key, 0, 4)

        #组织上下文模板
        context = {
            'types': types,
            'sku_orders': sku_orders,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'same_spu_skus': same_spu_skus
        }

        return render(request, 'detail.html', context)

#种类id  页码page  排序方式sort
#restful api -> 请求一种资源
#/list/id/page?sort=排序方式
#/list/id/page/sort
#/list?id=种类id&page=页码&sort=排序方式
class ListView(View):
    '''列表页'''
    def get(self, request, type_id, page):
        '''显示列表页'''
        #获取商品的种类信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            #商品不存在
            return redirect(reverse('goods:index'))

        #获取商品的分类信息
        types = GoodsType.objects.all()

        #获取排序的方式，并将商品信息进行排序
        #sort=default, 商品按id进行排序
        #sort=price, 商品按价格进行排序
        #sort=hot, 商品按价格进行排序
        sort = request.Get.get('sort')
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        #对数据进行分页
        paginator = Paginator(skus, 1)

        #获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        #获取第page页的Page实例对象
        skus_page = paginator.page(page)

        # todo: 进行页码的控制，页面上最多显示五个页码
        #1.总页数不足5页时， 显示所有页
        #2.当前页为前三页时， 显示1-5页
        #3.当前页为后三页时，显示后五页
        #4.显示前2页+当前页+后2页
        nums = paginator.num_pages
        if nums <= 5:
            pages = range(1, nums+1)
        elif page <= 3:
            pages = range(1, 6)
        elif nums-page <= 2:
            pages = range(nums-4, nums+1)
        else:
            pages = range(page-2, page+3)

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            #用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)

        #组织上下文模板
        context = {
            'type': type,
            'types': types,
            'skus_page': skus_page,
            'pages': pages,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'sort': sort
        }

        return render(request, 'list.html', context)