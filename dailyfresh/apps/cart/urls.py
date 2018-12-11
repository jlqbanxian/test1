from django.conf.urls import url
from apps.cart.views import CartAddView, CartInfoView, CartUpdateView, CartDeleteView
urlpatterns = [
    url(r'^add$', CartAddView.as_view(), name='cart_add'), #购物车添加
    url(r'^$', CartInfoView.as_view(), name='show'), #购物车信息展示
    url(r'^update$', CartUpdateView.as_view(), name='update'), #更新购物车记录
    url(r'^delete$', CartDeleteView.as_view(), name='delete'), #删除购物车记录
]
