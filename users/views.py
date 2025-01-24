from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.http import Http404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from qbanks.models import Qbank
from qbanks.utils import QbankService
from users.models import Account, Follow
from django.contrib.auth.decorators import login_required
from users.forms import UpdateUserForm, UpdateAccountForm
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import PasswordChangeView
from urllib.parse import unquote


def signup_view(request):
    context = {}
    if request.method == 'POST':
        context['next'] = request.POST.get('next', '/')

        # Initializes UserCreationForm with POST request parameters (username, password)
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # Creates user
            user = form.save()

            # Logs in user
            login(request, user)

            # Creates account with extra info for user
            Account.objects.create(user=user)

            # Redirects to previous page
            return redirect(context['next'])
    elif request.method == 'GET':
        context['next'] = request.GET.get('next', '/')

        # Initializes empty UserCreationForm
        form = UserCreationForm()
    else:
        raise Http404()

    context['form'] = form
    return render(request, 'users/signup.html', context)

def login_view(request):
    context = {}
    if request.method == 'POST':
        context['next'] = request.POST.get('next', '/')

        # Initializes AuthenticationForm with POST request parameters (username, password)
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            # Logs in user
            login(request, form.get_user())

            # Redirects to previous page
            return redirect(context['next'])
    elif request.method == 'GET':
        context['next'] = request.GET.get('next', '/')

        # Initializes empty AuthenticationForm
        form = AuthenticationForm()
    else:
        raise Http404()

    context['form'] = form
    return render(request, 'users/login.html', context)

@login_required
def logout_view(request):
    if request.method != 'POST':
        raise Http404()

    # Logs out user
    logout(request)

    # Redirects to previous page
    next_url = request.POST.get('next', '/')
    next_url = unquote(next_url)
    return redirect(next_url)

def profile(request):
    if request.method != 'GET':
        raise Http404

    context = {}

    username = request.GET.get('user')
    if username is None:
        raise Http404()

    # Gets user of the selected profile
    context['selected_user'] = get_object_or_404(User, username=username)
    
    # Gets qbanks of the selected user
    qbanks = Qbank.objects.filter(owner=context['selected_user'])
    context['qbanks'] = QbankService.annotate_basic_metrics(qbanks)

    # Gets qbank rating threshold
    context['ratings_threshold'] = QbankService.ratings_threshold

    # Checks if user follows selected_user, selected_user's followers and following users
    context['user_follow_statuses'] = {
        context['selected_user']: request.user.following.filter(following=context['selected_user']).exists() if request.user.is_authenticated else False
    }
    context['user_follow_statuses'].update({
        follow.follower: (request.user.following.filter(following=follow.follower).exists() if request.user.is_authenticated else False) for follow in context['selected_user'].followers.all()
    })
    context['user_follow_statuses'].update({
        follow.following: (request.user.following.filter(following=follow.following).exists() if request.user.is_authenticated else False) for follow in context['selected_user'].following.all()
    })

    # Gets profile section
    section = request.GET.get('section', 'qbanks_section')
    if section == 'qbanks_section' or section == 'followers_section' or section == 'following_section':
        context['section'] = section

    return render(request, 'users/profile.html', context)

@login_required
def edit_profile(request):
    context = {}
    if request.method == 'POST':
        old_username = request.user.username

        context['next'] = request.POST.get('next', '/')

        # Initializes UpdateUserForm with POST request parameters for the given user
        user_form = UpdateUserForm(request.POST, instance=request.user)

        # Initializes UpdateAccountForm with POST and FILES request parameters for the given account
        account_form = UpdateAccountForm(request.POST, request.FILES, instance=request.user.account)

        if user_form.is_valid() and account_form.is_valid():
            # Saves changes of user and its account
            user_form.save()
            account_form.save()

            # Redirects to home if the username changed
            context['next'] = '/' if request.user.username != old_username else context['next']
            return redirect(context['next'])
    elif request.method == 'GET':
        context['next'] = request.GET.get('next', '/')

        # Initializes UpdateUserForm and UpdateAccountForm with the values of the given user and its account
        user_form = UpdateUserForm(instance=request.user)
        account_form = UpdateAccountForm(instance=request.user.account)
    else:
        raise Http404()

    context['user_form'] = user_form
    context['account_form'] = account_form

    return render(request, 'users/edit_profile.html', context)

class ChangePasswordView(PasswordChangeView):
    template_name = 'users/change_password.html'

    def get_success_url(self):
        # Checks if 'next' parameter exists in GET or POST data
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse_lazy('qbanks:home')    # Default redirect URL

@login_required
def delete_user(request):
    context = {}
    if request.method == 'POST':
        context['next'] = request.POST.get('next', '/')

        # Initializes AuthenticationForm with POST request parameters
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            # Gets and deletes user
            user_to_delete = User.objects.get(username=request.user)
            user_to_delete.delete()

            # Redirects to previous page
            return redirect(context['next'])
    elif request.method == 'GET':
        context['next'] = request.GET.get('next', '/')

        # Initializes empty AuthenticationForm
        form = AuthenticationForm()
    else:
        raise Http404()

    context['form'] = form
    return render(request, 'users/delete_user.html', context)

def follow(request):
    if request.method != 'POST':
        raise Http404()

    username = request.POST.get('user')
    if username is None:
        raise Http404()

    # Gets user to follow
    selected_user = get_object_or_404(User, username=username)
    next_url = request.POST.get('next', '/')

    if not request.user.is_authenticated:
        # Redirects to login page
        next_url = reverse('users:login')
        query_string = f'?next={next_url}'
        return redirect(next_url+query_string)

    next_url = unquote(next_url)

    # Prevents user from following themselves
    if request.user == selected_user:
        return redirect(next_url)

    # Doesn't perform action if user is already following the selected user
    if Follow.objects.filter(follower=request.user, following=selected_user).exists():
        return redirect(next_url)

    # User follows the selected user
    Follow.objects.create(follower=request.user, following=selected_user)

    return redirect(next_url)

def unfollow(request):
    if request.method != 'POST':
        raise Http404()

    username = request.POST.get('user')
    if username is None:
        raise Http404()

    selected_user = get_object_or_404(User, username=username)
    next_url = request.POST.get('next', '/')

    if not request.user.is_authenticated:
        # Redirects to login page
        login_url = reverse('users:login')
        url = f'{login_url}?next={next_url}'
        return redirect(url)

    next_url = unquote(next_url)

    # Prevents user from unfollowing themselves (not really necessary)
    if request.user == selected_user:
        return redirect(next_url)

    # Doesn't perform action if user is not following the selected user
    follow_instance = Follow.objects.filter(follower=request.user, following=selected_user)
    if not follow_instance.exists():
        return redirect(next_url)

    # User unfollows the selected user
    follow_instance.delete()

    return redirect(next_url)
