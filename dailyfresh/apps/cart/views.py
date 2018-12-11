from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
# Create your views here.

#添加商品购物车
#1)请求方式， 采用ajax post
#如果涉及到数据的修改(新增，更新，删除)，采用post
#如果只涉及到数据的获取，采用get
#2) 传递参数： 商品id(sku_id) 商品数目(count)

#ajax发起的请求都在后台，在浏览器中是看不到效果
#/cart/add
class CartAddView(View):
    '''添加购物车'''
    def post(self, request):
        '''购物车添加'''
        user = request.user
        #判断用户是否登录
        if not user.is_authenticated():
            #用户未登录
            return JsonResponse({'res':0, 'errmsg':'清先登录'})

        #1.获取数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        #2.校验数据
        #校验数据是否完整
        if not all([sku_id, count]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        #校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            #数目出错
            return JsonResponse({'res':2, 'errmsg':'商品数目出错'})

        #校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            #商品不存在
            return JsonResponse({'res':3, 'errmsg':'商品不存在'})

        #3.业务处理：添加购物车
        #该商品用户已经添加过，就对数量进行累加
        #该商品用户未添加过，就新添加数据
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        # 先尝试获取sku_id的值 -> hget cart_key 属性
        #如果sku_id在hash中不存在，hget返回None
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            #商品存在，对数量进行累加
            count += int(cart_count)

        #判断商品数量是否大于库存
        if count > sku.stock:
            return JsonResponse({'res':4, 'errmsg':'商品库存不足'})

        #商品未添加过，添加商品
        #hset-> 如果sku_id已经存在，更新数据(覆盖)  如果sku_id不存在，添加数据
        conn.hset(cart_key, sku_id, count)

        #计算购物车中商品的条目数
        total_count = conn.hlen(cart_key)

        #4.返回应答
        return JsonResponse({'res':5, 'message':'添加成功', 'total_count':total_count})


#/cart
class CartInfoView(LoginRequiredMixin, View):
    '''购物车显示'''
    def get(self, requset):
        '''显示'''
        #获取登录的用户
        user = requset.user
        #获取用户购物车中商品的信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        #{'商品id'：商品数量}
        cart_dict = conn.hgetall(cart_key)

        skus = []

        #定义商品的总价格和总数量
        total_price = 0
        total_count = 0

        #遍历获取商品的信息
        for sku_id ,count in cart_dict.items():
            #根据商品的id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            #计算商品的小计
            amount = sku.price*int(count)
            #动态给sku对象添加一个属性amount，用来保存商品的小计
            sku.amount = amount
            #动态给sku对象添加一个属性count，保存购物车中对应商品的数量
            sku.count = count
            #添加
            skus.append(sku)
            #累加计算商品的总价格和总数量
            total_count += int(count)
            total_price += amount

        #组织上下文
        context = {
            'total_count': total_count,
            'total_price': total_price,
            'skus': skus
        }

        #使用模板
        return render(requset, 'cart.html', context)

#更新购物车记录
#采用ajax post请求
#前端需要传递的参数： 商品id(sku_id) 商品数目(count)
#/cart/update
class CartUpdateView(View):
    '''更新购物车记录'''
    def post(self, request):
        '''更新购物车记录'''
        user = request.user
        # 判断用户是否登录
        if not user.is_authenticated():
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '清先登录'})

        # 1.获取数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 2.校验数据
        # 校验数据是否完整
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            # 数目出错
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 3.业务处理：更新购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        #判断商品数量是否大于库存
        if count > sku.stock:
            return JsonResponse({'res':4, 'errmsg':'商品库存不足'})
        #更新
        conn.hset(cart_key, sku_id, count)

        #计算用户购物车中商品的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        #返回应答
        return JsonResponse({'res':5, 'message':'更新成功', 'total_count':total_count})

#删除购物车记录
#采用ajax post请求
#前端需要传递的参数： 商品id(sku_id)
#/cart/delete
class CartDeleteView(View):
    '''删除购物车记录'''
    def post(self,request):
        '''删除购物车记录'''
        user = request.user
        # 判断用户是否登录
        if not user.is_authenticated():
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '清先登录'})

        # 1.获取数据
        sku_id = request.POST.get('sku_id')

        # 2.校验数据
        # 校验数据是否完整
        if not all([sku_id]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 3.业务处理：删除购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        #删除
        conn.hdel(cart_key, sku_id)

        # 计算用户购物车中商品的总件数 {'1':4, '3':5}
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '删除成功', 'total_count': total_count})




