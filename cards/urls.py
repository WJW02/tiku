from django.urls import re_path
from cards import views


app_name = 'cards'

urlpatterns = [
    re_path('^cards_list/?$', views.cards_list, name='cards_list'),
    re_path('^create_card/?$', views.create_card, name='create_card'),
    re_path('^edit_card/?$', views.edit_card, name='edit_card'),
    re_path('^delete_card/?$', views.delete_card, name='delete_card'),
    re_path('^card/?$', views.card, name='card'),
]
