from django import forms
from qbanks.models import Topic, Qbank


class ExploreSearchForm(forms.Form):
    filter_choices = [
        (0, 'All'),
        (1, 'Recommended'),
        (2, 'Users'),
        (3, 'Data Science'),
        (4, 'Business'),
        (5, 'Computer Science'),
        (6, 'Information Technology'),
        (7, 'Language Learning'),
        (8, 'Health'),
        (9, 'Personal Development'),
        (10, 'Physical Science and Engineering'),
        (11, 'Social Sciences'),
        (12, 'Arts and Humanities'),
        (13, 'Math and Logic'),
    ]

    sort_choices = [
        (0, 'Trending'),
        (1, 'Popular'),
    ]

    filter = forms.ChoiceField(choices=filter_choices, required=False)
    sort = forms.ChoiceField(choices=sort_choices, required=False)
    text = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'placeholder': 'Search...'}))


class VaultSearchForm(forms.Form):
    filter_choices = [
        (0, 'All'),
        (1, 'Due today'),
    ]

    sort_choices = [
        (0, 'Name'),
        (1, 'Popular'),
    ]

    filter = forms.ChoiceField(choices=filter_choices, required=False)
    sort = forms.ChoiceField(choices=sort_choices, required=False)
    text = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'placeholder': 'Search...'}))


class QbankForm(forms.ModelForm):
    name = forms.CharField(
        max_length=63, 
        required=True, 
        widget=forms.TextInput(attrs={'placeholder': 'Qbank name'})
    )
    banner = forms.ImageField(
        required=False, 
        widget=forms.FileInput(attrs={'class': 'form-control-file'})
    )
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.all(),
        required=True
    )
    description = forms.CharField(
        max_length=1023, 
        required=False, 
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional description'})
    )

    class Meta:
        model = Qbank
        fields = ('name', 'banner', 'topic', 'description')
