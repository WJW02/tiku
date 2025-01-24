from django.db.models import Count, Value, Q
from django.db.models.functions import Coalesce
from datetime import timedelta
from django.utils import timezone


class UserService:
    @staticmethod
    def annotate_advanced_metrics(users):
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        return users.annotate(
            followers_count_last_7_days=Coalesce(Count('followers', distinct=True, filter=Q(followers__created_at__gte=seven_days_ago)), Value(0)),
            followers_count=Coalesce(Count('followers', distinct=True), Value(0)),
        )