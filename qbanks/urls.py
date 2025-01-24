from django.urls import path, re_path
from qbanks import views


app_name = 'qbanks'

urlpatterns = [
    re_path('^$', views.home, name='home'),
    re_path('^home/?$', views.home, name='home'),
    re_path('^explore/?$', views.explore, name='explore'),
    re_path('^vault/?$', views.vault, name='vault'),
    re_path('^create_qbank/?$', views.create_qbank, name='create_qbank'),
    re_path('^qbank/?$', views.qbank, name='qbank'),
    re_path('^favorite/?$', views.favorite, name='favorite'),
    re_path('^unfavorite/?$', views.unfavorite, name='unfavorite'),
    re_path('^rate/?$', views.rate, name='rate'),
    re_path('^unrate/?$', views.unrate, name='unrate'),
    re_path('^edit_qbank/?$', views.edit_qbank, name='edit_qbank'),
    re_path('^delete_qbank/?$', views.delete_qbank, name='delete_qbank'),
]
