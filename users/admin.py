from django.contrib import admin
from users.models import Account, Follow


admin.site.register(Account)
admin.site.register(Follow)