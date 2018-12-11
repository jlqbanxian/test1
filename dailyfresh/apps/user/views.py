from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.views.generic import View
from apps.user.models import User, Address
from apps.goods.models import GoodsSKU
from apps.order.models import OrderInfo, OrderGoods

from django.core.paginator import Paginator
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from celery_tasks.tasks import send_register_active_email
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from utils.mixin import LoginRequiredMixin
from django_redis import get_redis_connection
import re

# Create your views here.

#/user/register
def register(request):
    '''注册'''
    if request.method == 'GET':
        #显示注册页面
        return render(request, 'register.html')
    else:
        #进行注册处理
        '''注册处理'''
        # 获取注册信息
        username = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        cpwd = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行校验

        # 进行数据完整性校验
        if not all([username, email, pwd]):
            return render(request, 'register.html', {'errmsg': '数据填写不完整'})

        # 检测用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as e:
            # 用户名不存在
            user = None

        if user:
            # 用户名存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        # 进行邮箱检测
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        # 密码长度检测
        if len(pwd) not in [8, 21]:
            return render(request, 'register.html', {'errmsg': '请按规定长度设置'})

        # 密码确认检测
        if pwd != cpwd:
            return render(request, 'register.html', {'errmsg': '密码确认有误'})

        # 是否同意协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 处理事务：用户注册
        user = User.objects.create_user(username=username, email=email, password=pwd)
        user.is_active = 0
        user.save()

        # 返回应答
        return redirect(reverse('goods:index'))

#/user/register_handle
def register_handle(request):
    '''注册处理'''
    #获取注册信息
    username = request.POST.get('user_name')
    pwd = request.POST.get('pwd')
    cpwd = request.POST.get('cpwd')
    email = request.POST.get('email')
    allow = request.POST.get('allow')

    #进行校验

    #进行数据完整性校验
    if not all([username, email, pwd]):
        return render(request, 'register.html', {'errmsg':'数据填写不完整'})

    #检测用户名是否重复
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist as e:
        #用户名不存在
        user = None

    if user:
        #用户名存在
        return render(request, 'register.html', {'errmsg':'用户名已存在'})

    #进行邮箱检测
    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
        return render(request, 'register.html', {'errmsg':'邮箱格式不正确'})

    #密码长度检测
    if len(pwd) not in [8,21]:
        return render(request, 'register.html', {'errmsg':'请按规定长度设置'})

    #密码确认检测
    if pwd != cpwd:
        return render(request, 'register.html', {'errmsg':'密码确认有误'})

    #是否同意协议
    if allow != 'on':
        return render(request, 'register.html', {'errmsg':'请同意协议'})


    #处理事务：用户注册
    user = User.objects.create_user(username=username, email=email, password=pwd)
    user.is_active = 0
    user.save()

    #返回应答
    return redirect(reverse('goods:index'))


#/user/register
class RegisterView(View):
    '''注册'''

    #显示注册页面
    def get(self, request):
        '''显示注册页面'''
        return render(request, 'register.html')

    #进行注册处理
    def post(self, request):
        '''注册处理'''
        # 获取注册信息
        username = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        cpwd = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行校验

        # 进行数据完整性校验
        if not all([username, email, pwd]):
            return render(request, 'register.html', {'errmsg': '数据填写不完整'})

        # 检测用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as e:
            # 用户名不存在
            user = None

        if user:
            # 用户名存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        # 进行邮箱检测
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        # 密码长度检测
        if len(pwd) not in [8, 21]:
            return render(request, 'register.html', {'errmsg': '请按规定长度设置'})

        # 密码确认检测
        if pwd != cpwd:
            return render(request, 'register.html', {'errmsg': '密码确认有误'})

        # 是否同意协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 处理事务：用户注册
        user = User.objects.create_user(username=username, email=email, password=pwd)
        user.is_active = 0
        user.save()

        #发送激活邮件，包含激活链接 http://127.0.0.1/user/active/3
        #激活链接中需要包含用户的身份信息，并且要把身份信息进行加密

        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm':user.id}
        token = serializer.dumps(info) #bytes
        token = token.decode()

        #发邮件
        send_register_active_email.delay(email, username, token)
        # 组织邮件信息
        # subject = "天天生鲜欢迎信息"
        # message = ''
        # sender = settings.EMAIL_FROM
        # reciver = [email]
        # html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1><br/>请点击下面的链接进行激活<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (username, token, token)
        # send_mail(subject, message, sender, reciver, html_message=html_message)


        # 返回应答
        return redirect(reverse('goods:index'))

#/user/active/(token)
class ActiveView(View):
    '''激活'''
    def get(self, request, token):
        '''用户激活'''
        #进行解密,获取身份信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']

            # 激活用户
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 返回登录页面
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('激活链接已失效')

#/user/login
class LoginView(View):
    '''登录'''
    def get(self, request):
        '''显示登录页面'''
        #判断用户是否选择记住用户名
        if 'username' in request.COOKIES:
            #记住用户名
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checkd': checked})

    def post(self, request):
        '''登录处理'''
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remmeber = request.POST.get('remmeber')

        #判断数据完整性
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg':'数据信息不完整'})

        #业务处理:用户登录
        user = authenticate(username=username, password=password)
        if user is not None:
            # 用户名密码正确
            if user.is_active:
                #用户已激活

                #获取要跳转的页面
                next_url = request.GET.get('next', reverse('goods:index')) #默认跳转到商品主页面

                res = redirect(next_url) #HttpResponseRedirect对象
                #判断是否要记住用户名
                if remmeber == 'on':
                    #设置cookie记住用户名
                    res.set_cookie('username', username, max_age=7*24*3600)
                else:
                    res.delete_cookie('username')
                #记录激活状态
                login(request, user)
                #跳转到首页
                return res
            else:
                return render(request, 'login.html', {'errmsg':'用户未激活'})
        else:
            # 用户名密码错误
            render(request, 'login.html', {'errmsg':'用户名或密码错误'})

#/user/logout
class LogoutView(View):
    '''用户退出'''
    def get(self, request):
        '''退出登录'''
        #清楚session数据
        logout(request)

        #重定向到商品首页
        return  redirect(reverse('goods:index'))



#/user
class UserInfoView(LoginRequiredMixin, View):
    '''用户中心-信息页'''
    def get(self, request):
        #page_flag
        page_flag = 'userinfo'
        #request.user
        #如果用户未登录->AnonymousUser类的一个实例
        #如果用户登录->User类的一个实例
        #request.user.is_authenticated()
        #除了你给模板文件传递的模板变量之外，django框架会把request.user也传递给模板文件

        #获取用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user=user)

        #获取用户的历史浏览记录
        # from redis import StrictRedis
        # sr= StrictRedis(host='127.0.0.1', port=6379, db=9)
        con = get_redis_connection('default')

        history = "history_%d"%user.id

        #获取用户最近浏览的5个商品的id
        sku_ids = con.lrange(history, 0, 4)

        #从数据库中查询用户浏览的商品的具体信息
        #将数据按照浏览顺序进行排序
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        # goods_show = []
        # for id in sku_ids:
        #     for good in goods_li:
        #         if id == goods.id:
        #             goods_show.append(good)

        good_li = []
        for id in sku_ids:
            good = GoodsSKU.objects.get(id=id)
            good_li.append(good)

        #组织上下文
        context = {
            'page': page_flag,
            'address': address,
            'good_li': good_li
        }



        return render(request, 'user_center_info.html', context)

#/user/order
class UserOrderView(LoginRequiredMixin, View):
    '''用户中心-订单页'''
    def get(self, request, pages):
        #page_flag
        page_flag = 'userorder'

        #获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        #遍历获取订单商品的信息
        for order in orders:
            #根据order_id查询订单商品的信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            #遍历order_skus计算商品的小计
            for order_sku in order_skus:
                #计算小计
                amount = order_sku.price * order_sku.count
                #动态给order_sku添加属性amount，保存订单商品的小计
                order_sku.amount = amount

            # 动态给order添加属性status_name，保存订单状态标题
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

            # 动态给order添加属性order_skus，保存订单商品的信息
            order.order_skus = order_skus





        #分页
        paginator = Paginator(orders, 1)

        # 获取第page页的内容
        try:
            page = int(pages)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Page实例对象
        order_page = paginator.page(page)

        # todo: 进行页码的控制，页面上最多显示五个页码
        # 1.总页数不足5页时， 显示所有页
        # 2.当前页为前三页时， 显示1-5页
        # 3.当前页为后三页时，显示后五页
        # 4.显示前2页+当前页+后2页
        nums = paginator.num_pages
        if nums <= 5:
            pages = range(1, nums + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif nums - page <= 2:
            pages = range(nums - 4, nums + 1)
        else:
            pages = range(page - 2, page + 3)

        #组织上下文
        context = {
            'order_page': order_page,
            'pages': pages,
            'page_flag': page_flag
        }

        #使用模板
        return render(request, 'user_center_order.html', context)

#/user/address
class UserAddressView(LoginRequiredMixin, View):
    '''用户中心-地址页'''
    def get(self, request):
        #page_flag
        page_flag = 'useraddress'

        #获取登录用户对应User对象
        user = request.user
        # # 获取用户的默认地址
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 不存在默认地址
        #     address = None
        address = Address.objects.get_default_address(user=user)

        #使用模板
        return render(request, 'user_center_site.html', {'page':page_flag, 'address':address})

    def post(self, request):
        '''添加地址'''
        #1.获取地址信息
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        #2.校验信息
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg':'数据不完整'})

        #校验电话号码
        if not re.match(r'^1[3|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg':'号码格式不正确'})
        #3.业务处理：添加地址
        #如果用户已存在默认收货地址，添加的地址不作为默认收货地址，否则作为默认收货地址
        #获取登录用户对应User对象
        user = request.user

        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     #不存在默认地址
        #     address = None
        address = Address.objects.get_default_address(user=user)
        if address:
            is_default = False
        else:
            is_default = True

        #添加地址
        Address.objects.create(user=user, receiver=receiver, addr=addr, zip_code=zip_code, phone=phone, is_default=is_default)

        #4.返回应答，刷新地址页面
        return redirect(reverse('user:useraddress')) #get请求方式