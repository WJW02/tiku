from django.contrib import admin
from cards.models import Card, CardStatus


admin.site.register(Card)
admin.site.register(CardStatus)