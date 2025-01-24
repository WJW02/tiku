from django import forms

from django.contrib.auth.models import User
from users.models import Account


class UpdateUserForm(forms.ModelForm):
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', )

class UpdateAccountForm(forms.ModelForm):
    pfp = forms.ImageField(widget=forms.FileInput(attrs={'class': 'form-control-file'}))

    class Meta:
        model = Account
        fields = ('pfp', )
