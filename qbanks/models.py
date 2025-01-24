from django.db import models
from django.conf import settings


class Topic(models.Model):
    topic_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=127)
    banner = models.ImageField(upload_to='qbanks/files/topic_banners/', blank=True, null=True, default='qbanks/files/topic_banners/default.jpg')

    def __str__(self):
      return self.name

class Qbank(models.Model):
    qbank_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=63)  # Name of the Qbank
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='qbanks_owned')  # Foreign key to the user who owns the Qbank
    banner = models.ImageField(upload_to='qbanks/files/qbank_banners/', blank=True, null=True, default='qbanks/files/qbank_banners/default.jpg')
    topic = models.ForeignKey(Topic, related_name='qbanks', on_delete=models.CASCADE)
    description = models.TextField(max_length=1023, blank=True)  # Optional description field
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set when created
    updated_at = models.DateTimeField(auto_now=True)  # Automatically updated when the record changes

    def __str__(self):
        return self.name

class Favorite(models.Model):
    favorite_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    qbank = models.ForeignKey(Qbank, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensures each user/qbank pair is unique
        constraints = [
            models.UniqueConstraint(fields=['user', 'qbank'], name='unique_favorite'),
        ]

        # Orders by the most recent favorites first
        ordering = ['-created_at']

    def __str__(self):
        return f"Favorite by {self.user.username} for {self.qbank.name}"

class Rating(models.Model):
    rating_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings')
    qbank = models.ForeignKey(Qbank, on_delete=models.CASCADE, related_name='rated_by')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensures each user/qbank pair is unique
        constraints = [
            models.UniqueConstraint(fields=['user', 'qbank'], name='unique_rating'),
        ]

        # Orders by the most recent ratings first
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} rated {self.qbank} with {self.rating} stars"
