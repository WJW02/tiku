from django.urls import re_path
from users import views
from users.views import ChangePasswordView

app_name = 'users'

urlpatterns = [
    re_path('^signup/?$', views.signup_view, name='signup'),
    re_path('^login/?$', views.login_view, name='login'),
    re_path('^logout/?$', views.logout_view, name='logout'),
    re_path('^profile/?$', views.profile, name='profile'),
    re_path('^edit_profile/?$', views.edit_profile, name='edit_profile'),
    re_path('^change_password/?$', ChangePasswordView.as_view(), name='change_password'),
    re_path('^delete_user/?$', views.delete_user, name='delete_user'),
    re_path('^follow/?$', views.follow, name='follow'),
    re_path('^unfollow/?$', views.unfollow, name='unfollow'),
]
