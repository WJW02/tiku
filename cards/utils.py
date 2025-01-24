from cards.models import Card
from django.http import Http404
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta


class CardService:
    @staticmethod
    def schedule(card_status, difficulty):
        if difficulty == 'easy':
            # Checks if interval is zero
            if card_status.interval.total_seconds() < 86400:    
                # Sets the interval to 2 days
                card_status.interval = timedelta(days=2)
            else:
                # Doubles the interval
                card_status.interval *= 2    
        elif difficulty == 'good':
            # Checks if interval is zero
            if card_status.interval.total_seconds() < 86400:
                # Sets the interval to 1 days
                card_status.interval = timedelta(days=1)
            else:
                # Keeps the same interval
                pass    
        elif difficulty == 'hard':
            # Halves the interval
            card_status.interval /= 2    
        elif difficulty == 'again':
            # Resets to 0
            card_status.interval = timedelta(days=0)    
        else:
            raise Http404()
        
        card_status.last_review = timezone.now()
        card_status.due_date = timezone.now()+card_status.interval
        card_status.save()


class SearchEngine:
    @staticmethod
    def get_search_result(qbank, filter, sort, text):
        filter_choices = {
            '0': 'All',
        }

        sort_choices = {
            '0': 'Newest',
            '1': 'Oldest',
        }

        if filter not in filter_choices or sort not in sort_choices:
            raise Http404()

        cards = Card.objects.filter(qbank=qbank)
        
        if not cards:
            return None
        
        if sort_choices[sort] == 'Oldest':
            cards = cards.order_by('updated_at')

        cards = cards.filter(Q(question__icontains=text) | Q(answer__icontains=text))
        return cards