from django.db import models
from qbanks.models import Qbank
from django.contrib.auth.models import User


class Card(models.Model):
    card_id = models.AutoField(primary_key=True)
    qbank = models.ForeignKey(Qbank, on_delete=models.CASCADE, related_name='cards')
    question = models.TextField(max_length=255)
    image = models.ImageField(upload_to='cards/files/images', null=True, blank=True)
    answer = models.TextField(max_length=4095, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Sorting by most recent updated_at (descending order)
        ordering = ['-updated_at']

    def __str__(self):
        return f"Card {self.card_id} - {self.question[:50]}"

class CardStatus(models.Model):
    card_status_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='card_status')
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='card_status')
    interval = models.DurationField()
    last_review = models.DateTimeField()
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensures each user/card pair is unique
        unique_together = ('user', 'card')

        # Orders by due_date in ascending order by default
        ordering = ['due_date']

    def __str__(self):
        return f"CardStatus for User {self.user_id} and Card {self.card_id}"
