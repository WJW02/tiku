from django import forms
from cards.models import Card 

class SearchForm(forms.Form):
    filter_choices = [
        (0, 'All'),
    ]

    sort_choices = [
        (0, 'Newest'),
        (1, 'Oldest'),
    ]

    filter = forms.ChoiceField(choices=filter_choices, required=False)
    sort = forms.ChoiceField(choices=sort_choices, required=False)
    text = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'placeholder': 'Search...'}))

class CardForm(forms.ModelForm):
    question = forms.CharField(
        max_length=255, 
        required=True, 
        widget=forms.TextInput(attrs={'placeholder': 'Question'})
    )
    image = forms.ImageField(
        required=False, 
        widget=forms.FileInput(attrs={'class': 'form-control-file'})
    )
    answer = forms.CharField(
        max_length=4095, 
        required=False, 
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Answer'})
    )

    class Meta:
        model = Card
        fields = ('question', 'image', 'answer')
