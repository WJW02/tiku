from django.db import models
from django.conf import settings


class Account(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='account')
    pfp = models.ImageField(upload_to='users/files/pfps/', blank=True, null=True, default='users/files/pfps/default.jpg')

    def __str__(self):
        return f"Account of {self.user.username}"

class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='following', on_delete=models.CASCADE)
    following = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensures each follower/following pair is unique
        constraints = [
            models.UniqueConstraint(fields=['follower', 'following'], name='unique_follow'),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"
