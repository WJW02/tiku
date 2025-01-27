from django.test import TestCase, Client
from cards.models import Card, CardStatus
from qbanks.models import Qbank, Topic, Favorite
from django.contrib.auth.models import User
from cards.utils import CardService
from django.utils import timezone
from datetime import timedelta
from django.http import Http404
from django.urls import reverse


class SpacedRepetitionAlgorithmTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='test_user')
        self.topic = Topic.objects.create(name='test_topic')
        self.qbank = Qbank.objects.create(name='test_qbank', owner=self.user, topic=self.topic)

    # Test again rating scheduling
    def test_schedule_again_rating(self):
        card = Card.objects.create(qbank=self.qbank, question='test_question')
        card_status = CardStatus.objects.create(
            user=self.user,
            card=card,
            interval=timedelta(days=0),
            last_review=timezone.now(),
            due_date=timezone.now()
        )
        difficulty = 'again'
        CardService.schedule(card_status, difficulty)
        card_status.refresh_from_db()

        self.assertEqual(card_status.interval, timedelta(days=0))

    # Test hard rating scheduling when interval is 0
    def test_schedule_first_hard_rating(self):
        card = Card.objects.create(qbank=self.qbank, question='test_question')
        card_status = CardStatus.objects.create(
            user=self.user,
            card=card,
            interval=timedelta(days=0),
            last_review=timezone.now(),
            due_date=timezone.now()
        )
        difficulty = 'hard'
        CardService.schedule(card_status, difficulty)
        card_status.refresh_from_db()

        self.assertEqual(card_status.interval, timedelta(days=0))

    # Test good rating scheduling when interval is 0
    def test_schedule_first_good_rating(self):
        card = Card.objects.create(qbank=self.qbank, question='test_question')
        card_status = CardStatus.objects.create(
            user=self.user,
            card=card,
            interval=timedelta(days=0),
            last_review=timezone.now(),
            due_date=timezone.now()
        )
        difficulty = 'good'
        CardService.schedule(card_status, difficulty)
        card_status.refresh_from_db()

        self.assertEqual(card_status.interval, timedelta(days=1))

    # Test easy rating scheduling when interval is 0
    def test_schedule_first_easy_rating(self):
        card = Card.objects.create(qbank=self.qbank, question='test_question')
        card_status = CardStatus.objects.create(
            user=self.user,
            card=card,
            interval=timedelta(days=0),
            last_review=timezone.now(),
            due_date=timezone.now()
        )
        difficulty = 'easy'
        CardService.schedule(card_status, difficulty)
        card_status.refresh_from_db()

        self.assertEqual(card_status.interval, timedelta(days=2))

    # Test hard rating scheduling
    def test_schedule_hard_rating(self):
        card = Card.objects.create(qbank=self.qbank, question='test_question')
        card_status = CardStatus.objects.create(
            user=self.user,
            card=card,
            interval=timedelta(days=7),
            last_review=timezone.now(),
            due_date=timezone.now()
        )
        difficulty = 'hard'
        CardService.schedule(card_status, difficulty)
        card_status.refresh_from_db()

        self.assertEqual(card_status.interval, timedelta(days=3.5))

    # Test good rating scheduling
    def test_schedule_good_rating(self):
        card = Card.objects.create(qbank=self.qbank, question='test_question')
        card_status = CardStatus.objects.create(
            user=self.user,
            card=card,
            interval=timedelta(days=7),
            last_review=timezone.now(),
            due_date=timezone.now()
        )
        difficulty = 'good'
        CardService.schedule(card_status, difficulty)
        card_status.refresh_from_db()

        self.assertEqual(card_status.interval, timedelta(days=7))

    # Test easy rating scheduling
    def test_schedule_easy_rating(self):
        card = Card.objects.create(qbank=self.qbank, question='test_question')
        card_status = CardStatus.objects.create(
            user=self.user,
            card=card,
            interval=timedelta(days=7),
            last_review=timezone.now(),
            due_date=timezone.now()
        )
        difficulty = 'easy'
        CardService.schedule(card_status, difficulty)
        card_status.refresh_from_db()

        self.assertEqual(card_status.interval, timedelta(days=14))

    # Test invalid rating
    def test_schedule_invalid_rating(self):
        card = Card.objects.create(qbank=self.qbank, question='test_question')
        card_status = CardStatus.objects.create(
            user=self.user,
            card=card,
            interval=timedelta(days=7),
            last_review=timezone.now(),
            due_date=timezone.now()
        )
        difficulty = 'ok'

        with self.assertRaises(Http404):
            CardService.schedule(card_status, difficulty)


class CardViewTestCase(TestCase):
    def setUp(self):
        # Create test user and client
        self.user = User.objects.create_user(username='test_user', password='test_password')
        self.client = Client()
        self.client.login(username='test_user', password='test_password')

        # Create a Qbank owned by the test user
        self.topic = Topic.objects.create(name='test_topic')
        self.qbank = Qbank.objects.create(name='test_qbank', owner=self.user, topic=self.topic)

        # Create a Card in the Qbank
        self.card = Card.objects.create(qbank=self.qbank, question='test_question')

        # URL for the `card` view
        self.url = reverse('cards:card')

    # Test GET request with missing mode
    def test_get_missing_mode(self):
        response = self.client.get(self.url, {'card_id': self.card.card_id})

        # Check response status (404 expected due to missing card_id or difficulty)
        self.assertEqual(response.status_code, 404)

    # Test GET request in selection mode with a valid card_id
    def test_get_selection_mode_valid_card(self):
        response = self.client.get(self.url, {'mode': 'selection', 'card_id': self.card.card_id})

        # Check response status
        self.assertEqual(response.status_code, 200)

        # Check that the correct card is in the context
        self.assertEqual(response.context['card'], self.card)

    # Test GET request in selection mode with an invalid card_id
    def test_get_selection_mode_invalid_card(self):
        response = self.client.get(self.url, {'mode': 'selection', 'card_id': 999})  # Invalid card_id

        # Check response status (404 expected)
        self.assertEqual(response.status_code, 404)

    # Test GET request in selection mode with missing card_id
    def test_get_selection_mode_missing_card(self):
        response = self.client.get(self.url, {'mode': 'selection'})

        # Check response status
        self.assertEqual(response.status_code, 404)

    # Test GET request in random mode with a valid qbank_id
    def test_get_random_mode_valid_qbank(self):
        response = self.client.get(self.url, {'mode': 'random', 'qbank_id': self.qbank.qbank_id})

        # Check response status
        self.assertEqual(response.status_code, 200)

        # Check that a card from the Qbank is in the context
        self.assertEqual(response.context['card'], self.card)

    # Test GET request in random mode with an invalid qbank_id
    def test_get_random_mode_invalid_qbank(self):
        response = self.client.get(self.url, {'mode': 'random', 'qbank_id': 999})  # Invalid qbank_id

        # Check response status (404 expected)
        self.assertEqual(response.status_code, 404)

    # Test GET request in random mode with an missing qbank_id
    def test_get_random_mode_missing_qbank(self):
        response = self.client.get(self.url, {'mode': 'random'})  # Invalid qbank_id

        # Check response status (404 expected)
        self.assertEqual(response.status_code, 404)

    # Test GET request in spaced repetition mode as an authenticated user
    def test_get_spaced_repetition_mode_authenticated_user(self):
        Favorite.objects.create(user=self.user, qbank=self.qbank)

        # Create a CardStatus for the user
        card_status = CardStatus.objects.create(
            user=self.user,
            card=self.card,
            interval=timedelta(days=0),
            last_review=timezone.now(),
            due_date=timezone.now()
        )

        response = self.client.get(self.url, {'mode': 'spaced_repetition', 'qbank_id': self.qbank.qbank_id})

        # Check response status
        self.assertEqual(response.status_code, 200)

        # Check that the due card is in the context
        self.assertEqual(response.context['card'], self.card)

    # Test GET request in spaced repetition mode as an authenticated user with missing data
    def test_get_spaced_repetition_mode_authenticated_user_missing_data(self):
        Favorite.objects.create(user=self.user, qbank=self.qbank)

        # Create a CardStatus for the user
        card_status = CardStatus.objects.create(
            user=self.user,
            card=self.card,
            interval=timedelta(days=0),
            last_review=timezone.now(),
            due_date=timezone.now()
        )

        response = self.client.get(self.url, {'mode': 'spaced_repetition'})

        # Check response status
        self.assertEqual(response.status_code, 404)

    # Test GET request in spaced repetition mode as an unauthenticated user
    def test_get_spaced_repetition_mode_unauthenticated_user(self):
        self.client.logout()  # Log out the user
        response = self.client.get(self.url, {'mode': 'spaced_repetition', 'qbank_id': self.qbank.qbank_id})

        # Check redirect to login page
        self.assertRedirects(response, f"{reverse('users:login')}?next=/")

    # Test GET request in spaced repetition mode as an authenticated user that has not favorited the qbank
    def test_get_spaced_repetition_no_favorite(self):
        extra_card = Card.objects.create(qbank=self.qbank, question='test_question')

        response = self.client.get(self.url, {'mode': 'spaced_repetition', 'qbank_id': self.qbank.qbank_id})

        # Check response status
        self.assertEqual(response.status_code, 200)

        # Check that the qbank was favorited
        self.assertTrue(Favorite.objects.filter(user=self.user, qbank=self.qbank).exists())

        # Check that CardStatus objects were created for each card in the qbank
        card_statuses = CardStatus.objects.filter(user=self.user, card__qbank=self.qbank)
        self.assertEqual(card_statuses.count(), 2)

        # Verify the attributes of a CardStatus object
        card_status = card_statuses.get(card=self.card)
        self.assertEqual(card_status.user, self.user)
        self.assertEqual(card_status.card, self.card)
        self.assertEqual(card_status.interval, timedelta(days=0))

    # Test POST request with missing mode
    def test_post_missing_mode(self):
        response = self.client.post(self.url, {'card_id': self.card.card_id, 'next': '/'})

        # Check response status (404 expected due to missing card_id or difficulty)
        self.assertEqual(response.status_code, 404)

    # Test POST request in selection mode (no CardStatus update expected)
    def test_post_selection_mode(self):
        response = self.client.post(self.url, {'mode': 'selection', 'next': '/'})

        # Check redirect to the next page
        self.assertRedirects(response, '/')

    # Test POST request in random mode (no CardStatus update expected)
    def test_post_random_mode(self):
        response = self.client.post(self.url, {'mode': 'random', 'qbank_id': self.qbank.qbank_id, 'next': '/'})

        # Check redirect to the next page
        self.assertRedirects(response, f"{self.url}?mode=random&qbank_id={self.qbank.qbank_id}&next=/")

    # Test POST request in random mode with missing qbank_id
    def test_post_random_mode_missing_qbank(self):
        response = self.client.post(self.url, {'mode': 'random', 'next': '/'})

        # Check response status (404 expected)
        self.assertEqual(response.status_code, 404)

    # Test POST request in spaced repetition mode with valid data
    def test_post_spaced_repetition_mode_valid(self):
        Favorite.objects.create(user=self.user, qbank=self.qbank)

        # Create a CardStatus for the user
        card_status = CardStatus.objects.create(
            user=self.user,
            card=self.card,
            interval=timedelta(days=0),
            last_review=timezone.now(),
            due_date=timezone.now()
        )

        response = self.client.post(self.url, {
            'mode': 'spaced_repetition',
            'qbank_id': self.qbank.qbank_id,
            'card_id': self.card.card_id,
            'difficulty': 'easy',
            'next': '/'
        })

        # Eventually check if CardStatus was updated

        # Check redirect to the next due card
        self.assertRedirects(response, f"{self.url}?mode=spaced_repetition&qbank_id={self.qbank.qbank_id}&next=/")

    # Test POST request in spaced repetition mode with invalid data
    def test_post_spaced_repetition_mode_invalid_data(self):
        Favorite.objects.create(user=self.user, qbank=self.qbank)

        # Create a CardStatus for the user
        card_status = CardStatus.objects.create(
            user=self.user,
            card=self.card,
            interval=timedelta(days=0),
            last_review=timezone.now(),
            due_date=timezone.now()
        )

        response = self.client.post(self.url, {
            'mode': 'spaced_repetition',
            'qbank_id': 999,
            'card_id': 999,
            'difficulty': 'easy',
            'next': '/'
        })

        # Check response status (404 expected)
        self.assertEqual(response.status_code, 404)

    # Test POST request in spaced repetition mode with missing card_id or difficulty
    def test_post_spaced_repetition_mode_missing_data(self):
        response = self.client.post(self.url, {
            'mode': 'spaced_repetition',
            'qbank_id': self.qbank.qbank_id,
            'next': '/'
        })

        # Check response status (404 expected due to missing card_id or difficulty)
        self.assertEqual(response.status_code, 404)

    # Test POST request in spaced repetition mode as an authenticated user that has not favorited the qbank
    def test_post_spaced_repetition_no_favorite(self):
        extra_card = Card.objects.create(qbank=self.qbank, question='test_question')

        response = self.client.post(self.url, {
            'mode': 'spaced_repetition',
            'qbank_id': self.qbank.qbank_id,
            'card_id': self.card.card_id,
            'difficulty': 'easy',
            'next': '/'
        })

        # Check that the qbank was favorited
        self.assertTrue(Favorite.objects.filter(user=self.user, qbank=self.qbank).exists())

        # Check that CardStatus objects were created for each card in the qbank
        card_statuses = CardStatus.objects.filter(user=self.user, card__qbank=self.qbank)
        self.assertEqual(card_statuses.count(), 2)

        # Verify the attributes of a CardStatus object
        card_status = card_statuses.get(card=self.card)
        self.assertEqual(card_status.user, self.user)
        self.assertEqual(card_status.card, self.card)
        self.assertEqual(card_status.interval, timedelta(days=2))

        # Check redirect to the next due card
        self.assertRedirects(response, f"{self.url}?mode=spaced_repetition&qbank_id={self.qbank.qbank_id}&next=/")

    # Test an unsupported HTTP method (e.g., PUT)
    def test_invalid_request_method(self):
        response = self.client.put(self.url)

        # Check response status (404 expected)
        self.assertEqual(response.status_code, 404)
