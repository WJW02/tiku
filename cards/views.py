from django.shortcuts import render, redirect, get_object_or_404
from cards.models import Card, CardStatus
from qbanks.models import Qbank, Favorite
from cards.forms import SearchForm, CardForm
from django.http import Http404
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth.models import User
from urllib.parse import unquote
from cards.utils import SearchEngine, CardService


def cards_list(request):
    if request.method != 'GET':
        raise Http404()

    context = {}

    # Initializes SearchForm with GET request parameters (filter, sort, text)
    form = SearchForm(request.GET)

    qbank_id = request.GET.get('qbank_id')
    context['qbank'] = get_object_or_404(Qbank.objects.all(), qbank_id=qbank_id)

    # The form is always valid because fields are not required (unless manually passing incorrect values through url)
    if not form.is_valid():
        raise Http404()

    # Uses query string parameters instead of form for compatibility with login and logout page
    filter = request.GET.get('filter')
    sort = request.GET.get('sort')

    if filter and sort:
        # Sets search parameters
        context['filter'] = filter
        context['sort'] = sort
        context['text'] = request.GET.get('text', '')

        # Initializes SearchForm with search parameters (text as well)
        form = SearchForm(initial=context)

        # Gets resulting cards from search
        context['cards'] = SearchEngine.get_search_result(context['qbank'], context['filter'], context['sort'], context['text'])
    else:
        raise Http404()

    context['form'] = form
    return render(request, 'cards/cards_list.html', context)

# Test if a user can add card to qbank of another user
@login_required
def create_card(request):
    context = {}
    qbank_id = request.GET.get('qbank_id') or request.POST.get('qbank_id')
    context['qbank'] = get_object_or_404(Qbank.objects.all(), qbank_id=qbank_id)


    # Prevents users that are not the owner from adding cards to the qbank
    if context['qbank'].owner != request.user:
        raise Http404()

    if request.method == 'POST':
        context['next'] = request.POST.get('next', '/')

        # Initializes CardForm with POST and FILES request parameters (question, answer)
        form = CardForm(request.POST, request.FILES)
        if form.is_valid():
            card_data = {
                'question': form.cleaned_data['question'],
                'qbank': context['qbank'],
                'answer': form.cleaned_data['answer'],
            }
                
            # Only include 'image' if it is not None
            if form.cleaned_data['image']:
                card_data['image'] = form.cleaned_data['image']

            # Adds card to the qbank
            card = Card.objects.create(**card_data)

            # Gets list of users that favorited the qbank
            users = User.objects.filter(favorites__qbank=context['qbank'])

            # Creates CardStatus for the newly added card for every user that favorited the qbank
            for user in users:
                card_status_data = {
                    'user': user,
                    'card': card,
                    'interval': timedelta(days=0),
                    'last_review': timezone.now(),
                    'due_date': timezone.now()
                }
                CardStatus.objects.create(**card_status_data)

            # Go back to cards list
            next_url = reverse('cards:cards_list')
            query_string = f"?qbank_id={context['qbank'].qbank_id}&filter=0&sort=0"
            return redirect(next_url+query_string)
    elif request.method == 'GET':
        context['next'] = request.GET.get('next', '/')

        # Initializes empty CardForm
        form = CardForm()
    else:
        raise Http404()
    
    context['form'] = form
    return render(request, 'cards/create_card.html', context)

@login_required
def edit_card(request):
    context = {}

    context['card_id'] = request.POST.get('card_id') or request.GET.get('card_id')
    if context['card_id'] is None:
        raise Http404()

    card = get_object_or_404(Card, card_id=context['card_id'])

    # Prevents users that are not the owner from editing cards of the qbank
    if card.qbank.owner != request.user:
        raise Http404()

    if request.method == 'POST':
        context['next'] = request.POST.get('next', '/')

        # Initializes CardForm with POST and FILES request parameters for the given card
        form = CardForm(request.POST, request.FILES, instance=card)
        if form.is_valid():
            form.save()
            return redirect(context['next'])
    else:
        context['next'] = request.GET.get('next', '/')

        # Initializes CardForm with the values of the given card
        form = CardForm(instance=card)
    
    context['form'] = form
    return render(request, 'cards/edit_card.html', context)

def delete_card(request):
    if request.method != 'POST':
        raise Http404()

    card_id = request.POST.get('card_id')
    if card_id is None:
        raise Http404()

    card = get_object_or_404(Card, card_id=card_id)
    next_url = request.POST.get('next', '/')

    if not request.user.is_authenticated:
        # Redirects to login page
        login_url = reverse('users:login')
        query_string = f'?next={next_url}'
        return redirect(login_url+query_string)

    next_url = unquote(next_url)

    # Prevents users that are not the owner from deleting cards of the qbank
    if card.qbank.owner != request.user:
        return redirect(next_url)

    card.delete()

    return redirect(next_url)

def card(request):
    context = {}
    context['mode'] = request.GET.get('mode') or request.POST.get('mode')
    card_id = request.GET.get('card_id') or request.POST.get('card_id')
    qbank_id = request.GET.get('qbank_id') or request.POST.get('qbank_id')
    # If it's a GET request (fetches card to show on page)
    if request.method == 'GET':
        context['next'] = request.GET.get('next', '/')
        
        # If request comes from cards_list (card_id, mode=selection)
        if card_id and context['mode'] and context['mode'] == 'selection':
            # Gets the specified card
            context['card'] = get_object_or_404(Card, card_id=card_id)

        # If request comes from random button (qbank_id, mode=random)
        elif qbank_id and context['mode'] and context['mode'] == 'random':
            context['qbank'] = get_object_or_404(Qbank, qbank_id=qbank_id)

            # Gets random card from qbank
            context['card'] = Card.objects.filter(qbank=context['qbank']).order_by('?').first()

        # If request comes from spaced repetition button (qbank_id, mode=spaced_repetition)
        # (must be logged in and must have favorited the qbank, if not call favorite for both cases)
        elif qbank_id and context['mode'] and context['mode'] == 'spaced_repetition':        
            context['qbank'] = get_object_or_404(Qbank, qbank_id=qbank_id)
            if not request.user.is_authenticated:
                login_url = reverse('users:login')
                query_string = f"?next={context['next']}"
                return redirect(login_url+query_string)

            # If user has not favorited the qbank
            if not Favorite.objects.filter(qbank=context['qbank'], user=request.user).exists():
                # User favorites qbank 
                Favorite.objects.create(user=request.user, qbank=context['qbank'])

                # Gets list of cards of the qbank
                cards = Card.objects.filter(qbank=context['qbank'])

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

            # Gets first of the due cards (oldest due date)
            card_status = CardStatus.objects.filter(
                user=request.user,
                card__qbank=context['qbank'],
                due_date__lte=timezone.now()
            ).first()
            if card_status:
                context['card'] = card_status.card
        else:
            raise Http404()

        return render(request, 'cards/card.html', context)

    # If it's a POST request (updates CardStatus and redirects to next page)
    elif request.method == 'POST':
        next_url = request.POST.get('next', '/')

        # If request comes from cards_list, don't update CardStatus
        if context['mode'] and context['mode'] == 'selection':
            # Redirects to cards list
            return redirect(next_url)

        # If request comes from random button, don't update CardStatus
        elif qbank_id and context['mode'] and context['mode'] == 'random':
            # Redirects to next random card
            card_url = reverse('cards:card')
            query_string = f"?mode={context['mode']}&qbank_id={qbank_id}&next={next_url}"
            return redirect(card_url+query_string)

        # If request comes from spaced repetition button
        # (must be logged in and must have favorited the qbank, if not call favorite for both cases)
        elif qbank_id and context['mode'] and context['mode'] == 'spaced_repetition':
            context['qbank'] = get_object_or_404(Qbank, qbank_id=qbank_id)

            if not request.user.is_authenticated:
                # Redirects to login page
                login_url = reverse('users:login')
                query_string = f"?next={next_url}"
                return redirect(login_url+query_string)

            if not Favorite.objects.filter(qbank=context['qbank'], user=request.user).exists():
                Favorite.objects.create(user=request.user, qbank=context['qbank'])

                # Get list of cards of the qbank
                cards = Card.objects.filter(qbank=context['qbank'])

                # For each card create a card status for the logged in user
                for card in cards:
                    card_status_data = {
                        'user': request.user,
                        'card': card,
                        'interval': timedelta(days=0),
                        'last_review': timezone.now(),
                        'due_date': timezone.now()
                    }
                    CardStatus.objects.create(**card_status_data)

            difficulty = request.POST.get('difficulty')
            if not card_id or not difficulty:
                raise Http404()
            
            # Schedules card based on user rating
            card = get_object_or_404(Card, card_id=card_id)
            card_status = CardStatus.objects.get(user=request.user, card=card)
            CardService.schedule(card_status, difficulty) 
            
            # Redirects to next due card
            card_url = reverse('cards:card')
            query_string = f"?mode={context['mode']}&qbank_id={qbank_id}&next={next_url}"
            print(card_url+query_string)
            return redirect(card_url+query_string)
        else:
            raise Http404()
    else:
        raise Http404()
