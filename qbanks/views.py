from django.shortcuts import render, redirect, get_object_or_404
from qbanks.models import Qbank, Topic, Favorite, Rating
from cards.models import Card, CardStatus
from qbanks.forms import ExploreSearchForm, VaultSearchForm, QbankForm
from django.http import Http404
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from urllib.parse import unquote
from qbanks.utils import SearchEngine, QbankService
from django.core.paginator import Paginator


def home(request):
    context = {}
    if request.user.is_authenticated:
        # Gets recommended qbanks
        recommended_qbanks = SearchEngine.get_explore_search_result(request.user, '1', '0', '')
        context['recommended_qbanks'] = recommended_qbanks[:3] if recommended_qbanks is not None else None

    # Gets trending qbanks
    trending_qbanks = SearchEngine.get_explore_search_result(request.user, '0', '0', '')
    context['trending_qbanks'] = trending_qbanks[:3] if trending_qbanks is not None else None

    # Gets popular qbanks
    popular_qbanks = SearchEngine.get_explore_search_result(request.user, '0', '1', '')
    context['popular_qbanks'] = popular_qbanks[:3] if popular_qbanks is not None else None

    # Gets qbank rating threshold
    context['ratings_threshold'] = QbankService.ratings_threshold
    return render(request, "qbanks/home.html", context)

def explore(request):
    if request.method != 'GET':
        raise Http404()

    context = {}
    
    # Initializes ExploreSearchForm with GET request parameters (filter, sort, text)
    form = ExploreSearchForm(request.GET)

    # The form is always valid because fields are not required (unless manually passing incorrect values through url)
    if form.is_valid():
        # Uses query string parameters instead of form for compatibility with login and logout page
        filter = request.GET.get('filter')
        sort = request.GET.get('sort')

        # Gets result of search (takes filter and sort from query string)
        if filter and sort:
            # Sets search parameters
            context['filter'] = filter
            context['sort'] = sort
            context['text'] = request.GET.get('text', '')

            # Initializes ExploreSearchForm with search parameters (text as well)
            form = ExploreSearchForm(initial=context)

            # If it's searching users
            if filter == '2':
                # Gets resulting users from search
                users = SearchEngine.get_explore_search_result(request.user, context['filter'], context['sort'], context['text'])

                if users:
                    # Checks if current user follows the resulting users
                    context['user_follow_statuses'] = {
                        selected_user: (request.user.following.filter(following=selected_user).exists() if request.user.is_authenticated else False) for selected_user in users
                    }

                    # Gets subset of 18 users per page
                    paginator = Paginator(users, 18)
                    page = request.GET.get('page')
                    context['users'] = paginator.get_page(page)

            # If it's searching qbanks
            else:
                # Gets qbank rating threshold
                context['ratings_threshold'] = QbankService.ratings_threshold

                # Gets resulting qbanks from search
                qbanks = SearchEngine.get_explore_search_result(request.user, context['filter'], context['sort'], context['text'])

                # Gets subset of 9 qbanks per page
                if qbanks:
                    paginator = Paginator(qbanks, 9)
                    page = request.GET.get('page')
                    context['qbanks'] = paginator.get_page(page)

        else: # If it's first load of explore page (query string parameters not set)
            # Gets topics
            context['topics'] = Topic.objects.order_by('topic_id')

            # Gets dictionary of topic index values for search filter
            context['filter_choices'] = SearchEngine.topic_filter_choices
    else:
        raise Http404()

    context['form'] = form
    return render(request, 'qbanks/explore.html', context)

@login_required
def vault(request):
    if request.method != 'GET':
        raise Http404()

    context = {}

    # Initializes VaultSearchForm with GET request parameters (filter, sort, text)
    form = VaultSearchForm(request.GET)

    # The form is always valid because fields are not required (unless manually passing incorrect values through url)
    if form.is_valid():
        # Uses query string parameters instead of form for compatibility with login and logout page
        filter = request.GET.get('filter')
        sort = request.GET.get('sort')

        # Gets result of search (takes filter and sort from query string)
        if filter and sort:
            # Set search parameters
            context['filter'] = filter
            context['sort'] = sort
            context['text'] = request.GET.get('text', '')

            # Initializes VaultSearchForm with search parameters (text as well)
            form = VaultSearchForm(initial=context)

            # Gets qbank rating threshold
            context['ratings_threshold'] = QbankService.ratings_threshold

            # Gets resulting qbanks and number of cards due today for each qbank from search
            qbanks, context['cards_due_today'] = SearchEngine.get_vault_search_result(request.user, context['filter'], context['sort'], context['text'])

            # Gets subset of 9 qbanks per page
            if qbanks:
                paginator = Paginator(qbanks, 9)
                page = request.GET.get('page')
                context['qbanks'] = paginator.get_page(page)
        else:
            raise Http404()
    else:
        raise Http404()

    context['form'] = form
    return render(request, 'qbanks/vault.html', context)

@login_required
def create_qbank(request):
    context = {}
    if request.method == 'POST':
        context['next'] = request.POST.get('next', '/')

        # Initializes QbankForm with POST and FILES request parameters (name, topic, description, banner)
        form = QbankForm(request.POST, request.FILES)
        if form.is_valid():
            qbank_data = {
                'name': form.cleaned_data['name'],
                'owner': request.user,
                'topic': form.cleaned_data['topic'],
                'description': form.cleaned_data['description'],
            }
            
            # Only includes 'banner' if it is not None
            # If it is None it will user default banner
            if form.cleaned_data['banner']:
                qbank_data['banner'] = form.cleaned_data['banner']

            # Creates new qbank
            qbank = Qbank.objects.create(**qbank_data)

            # Go to page of new qbank
            next_url = reverse('qbanks:qbank')
            query_string = f'?qbank_id={qbank.qbank_id}'
            return redirect(next_url+query_string)
    elif request.method == 'GET':
        context['next'] = request.GET.get('next', '/')
        form = QbankForm()
    else:
        raise Http404()
    
    context['form'] = form
    return render(request, 'qbanks/create_qbank.html', context)

def qbank(request):
    if request.method != 'GET':
        raise Http404()

    qbank_id = request.GET.get('qbank_id')
    if qbank_id is None:
        raise Http404()

    context = {}

    # Gets qbank with its favorites count and average rating
    context['qbank'] = get_object_or_404(QbankService.annotate_basic_metrics(Qbank.objects.all()), qbank_id=qbank_id)

    if request.user.is_authenticated:
        # Checks if the qbank is favorited by current user
        if context['qbank'].favorited_by.filter(user=request.user).exists():
            context['is_favorited'] = True
            context['cards_due_today'] = CardStatus.objects.filter(
                user=request.user,
                card__qbank=context['qbank'],
                due_date__lte=timezone.now()
            ).count()

        # Checks if the qbank is rated by current user
        context['is_rated'] = context['qbank'].rated_by.filter(user=request.user).exists()

    # Gets qbank rating threshold
    context['ratings_threshold'] = QbankService.ratings_threshold

    return render(request, "qbanks/qbank.html", context)

# The choice to not use @login_required is to not redirect to this action after login
def favorite(request):
    if request.method != 'POST':
        raise Http404()

    qbank_id = request.POST.get('qbank_id')
    if qbank_id is None:
        raise Http404()

    qbank = get_object_or_404(Qbank, qbank_id=qbank_id)
    next_url = request.POST.get('next', '/')

    if not request.user.is_authenticated:
        # Redirects to login page
        login_url = reverse('users:login')
        query_string = f'?next={next_url}'
        return redirect(login_url+query_string)

    next_url = unquote(next_url)

    # Doesn't perform action if user has already favorited the qbank
    if Favorite.objects.filter(user=request.user, qbank=qbank).exists():
        return redirect(next_url)

    # User favorites the qbank
    Favorite.objects.create(user=request.user, qbank=qbank)

    # Gets list of cards of the qbank
    cards = Card.objects.filter(qbank=qbank)

    # For each card it creates a card status for the logged in user
    for card in cards:
        card_status_data = {
          'user': request.user,
          'card': card,
          'interval': timedelta(days=0),
          'last_review': timezone.now(),
          'due_date': timezone.now()
        }
        CardStatus.objects.create(**card_status_data)

    return redirect(next_url)

# The choice to not use @login_required is to not redirect to this action after login
# (even though normally users wouldn't be able to access to unfavorite button if not logged in)
def unfavorite(request):
    if request.method != 'POST':
        raise Http404()

    qbank_id = request.POST.get('qbank_id')
    if qbank_id is None:
        raise Http404()

    qbank = get_object_or_404(Qbank, qbank_id=qbank_id)
    next_url = request.POST.get('next', '/')

    if not request.user.is_authenticated:
        # Redirects to login page
        login_url = reverse('users:login')
        query_string = f'?next={next_url}'
        return redirect(login_url+query_string)

    next_url = unquote(next_url)

    # Doesn't perform action if user has not favorited the qbank
    favorite_instance = Favorite.objects.filter(user=request.user, qbank=qbank)
    if not favorite_instance.exists():
        return redirect(next_url)

    # User unfavorites the qbank
    favorite_instance.delete()

    # Gets list of cards of the qbank
    cards = Card.objects.filter(qbank=qbank)

    # For each card delete the card status for the logged in user
    for card in cards:
        card_status = CardStatus.objects.filter(card=card, user=request.user)
        if card_status:
            card_status.delete()

    return redirect(next_url)

# The choice to not use @login_required is to not redirect to this action after login
def rate(request):
    if request.method != 'POST':
        raise Http404()

    qbank_id = request.POST.get('qbank_id')
    rating = request.POST.get('rating')

    if qbank_id is None or rating is None:
        raise Http404()

    qbank = get_object_or_404(Qbank, qbank_id=qbank_id)
    next_url = request.POST.get('next', '/')

    if not request.user.is_authenticated:
        # Redirects to login page
        login_url = reverse('users:login')
        query_string = f'?next={next_url}'
        return redirect(login_url+query_string)

    next_url = unquote(next_url)

    # Doesn't perform action if user has already rated the qbank
    if Rating.objects.filter(user=request.user, qbank=qbank).exists():
        return redirect(next_url)

    # Doesn't perform action if user is the owner of the qbank
    if qbank.owner == request.user:
        return redirect(next_url)

    # User rates the qbank
    Rating.objects.create(user=request.user, qbank=qbank, rating=int(rating))

    return redirect(next_url)

# The choice to not use @login_required is to not redirect to this action after login
# (even though normally users wouldn't be able to access to unrate button if not logged in)
def unrate(request):
    if request.method != 'POST':
        raise Http404()

    qbank_id = request.POST.get('qbank_id')
    if qbank_id is None:
        raise Http404()

    qbank = get_object_or_404(Qbank, qbank_id=qbank_id)
    next_url = request.POST.get('next', '/')

    if not request.user.is_authenticated:
        # Redirects to login page
        login_url = reverse('users:login')
        query_string = f'?next={next_url}'
        return redirect(login_url+query_string)

    next_url = unquote(next_url)

    # Doesn't perform action if user has not rated the qbank
    rating_instance = Rating.objects.filter(user=request.user, qbank=qbank)
    if not rating_instance.exists():
        return redirect(next_url)

    # User unrates the qbank
    rating_instance.delete()

    return redirect(next_url)

@login_required
def edit_qbank(request):
    context = {}
    context['qbank_id'] = request.POST.get('qbank_id') or request.GET.get('qbank_id')
    if context['qbank_id'] is None:
        raise Http404()

    qbank = get_object_or_404(Qbank, qbank_id=context['qbank_id'])

    # Prevents users that are not the owner from editing the qbank
    if qbank.owner != request.user:
        raise Http404()

    if request.method == 'POST':
        context['next'] = request.POST.get('next', '/')

        # Initializes QbankForm with POST and FILES request parameters for the given qbank
        form = QbankForm(request.POST, request.FILES, instance=qbank)
        if form.is_valid():
            form.save()
            return redirect(context['next'])
    else:
        context['next'] = request.GET.get('next', '/')

        # Initializes QbankForm with the values of the given qbank
        form = QbankForm(instance=qbank)
    
    context['form'] = form 
    return render(request, 'qbanks/edit_qbank.html', context)

def delete_qbank(request):
    if request.method != 'POST':
        raise Http404()

    qbank_id = request.POST.get('qbank_id')
    if qbank_id is None:
        raise Http404()

    qbank = get_object_or_404(Qbank, qbank_id=qbank_id)
    next_url = request.POST.get('next', '/')

    if not request.user.is_authenticated:
        # Redirects to login page
        login_url = reverse('users:login')
        query_string = f'?next={next_url}'
        return redirect(login_url+query_string)

    next_url = unquote(next_url)

    # Prevents users that are not the owner from deleting the qbank
    if qbank.owner != request.user:
        return redirect(next_url)

    qbank.delete()

    # Redirects to homepage
    next_url = '/'
    return redirect(next_url)
