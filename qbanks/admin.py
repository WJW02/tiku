from django.contrib import admin
from qbanks.models import Qbank, Topic, Favorite, Rating


admin.site.register(Topic)
admin.site.register(Qbank)
admin.site.register(Favorite)
admin.site.register(Rating)
