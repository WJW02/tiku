import pandas as pd
from qbanks.models import Rating, Qbank
from django.db.models import Count, Avg, Value, FloatField, Q
from django.db.models.functions import Coalesce
from django.contrib.auth.models import User
from cards.models import CardStatus
from django.http import Http404
from datetime import timedelta
from django.utils import timezone
from users.utils import UserService
from sklearn.metrics.pairwise import cosine_similarity


class QbankService:
    ratings_threshold = [4.5, 3.5, 2.5, 1.5, 0.5]

    @staticmethod
    def annotate_basic_metrics(qbanks):
        return qbanks.annotate(
            favorites_count=Coalesce(Count('favorited_by', distinct=True), Value(0)),
            avg_rating=Coalesce(Avg('rated_by__rating'), Value(0), output_field=FloatField())
        )

    @staticmethod
    def annotate_advanced_metrics(qbanks):
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        return qbanks.annotate(
            favorites_count_last_7_days=Coalesce(Count('favorited_by', distinct=True, filter=Q(favorited_by__created_at__gte=seven_days_ago)), Value(0)),
            favorites_count=Coalesce(Count('favorited_by', distinct=True), Value(0)),
            avg_rating=Coalesce(Avg('rated_by__rating'), Value(0), output_field=FloatField())
        )


class RecommendationEngine:
    @staticmethod
    def recommend(user: User):
        # 1. Create user-qbank matrix
        user_qbank_matrix = RecommendationEngine.get_user_qbank_matrix()
        if user_qbank_matrix.empty:
            return None

        # 2. Normalize ratings in user-qbank matrix
        user_qbank_matrix_norm = RecommendationEngine.normalize(user_qbank_matrix)

        # 3. Calculate similarity using Pearson correlation
        user_similarity = RecommendationEngine.get_user_similarity(user_qbank_matrix_norm)
        if user_similarity.empty:
            return None

        # 4. Get top n similar users
        similar_users = RecommendationEngine.get_similar_users(user_similarity, user, 10, 0.3)
        if similar_users.empty:
            return None

        # 5. Narrow down qbank pool
        similar_user_qbanks = RecommendationEngine.get_similar_user_qbanks(user_qbank_matrix_norm, similar_users, user)
        if similar_user_qbanks.empty:
            return None

        # 6. Recommend qbanks
        recommended_qbanks = RecommendationEngine.get_recommended_qbanks(similar_users, similar_user_qbanks, user, 9)

        return recommended_qbanks

    @staticmethod
    def get_user_qbank_matrix():
        # Query data from the model
        ratings = Rating.objects.all()

        if not ratings:
            return pd.DataFrame()

        # Prepare data for DataFrame
        data = [
            {
                'username': rating.user.username,
                'qbank_id': rating.qbank.qbank_id,
                'rating': rating.rating
            }
            for rating in ratings
        ]

        # Create DataFrame
        df = pd.DataFrame(data)

        # Pivot the DataFrame to create a user-qbank matrix
        user_qbank_matrix = df.pivot_table(index='username', columns='qbank_id', values='rating')
        
        return user_qbank_matrix

    @staticmethod
    def normalize(user_qbank_matrix: pd.DataFrame):
        # Calculates the mean of each row and subtracts it from each element of the corresponding row
        # This normalizes the ratings around 0
        return user_qbank_matrix.subtract(user_qbank_matrix.mean(axis=1), axis='rows')
    
    @staticmethod
    def get_user_similarity(user_qbank_matrix_norm: pd.DataFrame):
        # Get user similarity matrix (numpy array)
        user_similarity = cosine_similarity(user_qbank_matrix_norm.fillna(0))
        # Return user similarity matrix (dataframe)
        return pd.DataFrame(user_similarity, index=user_qbank_matrix_norm.index, columns=user_qbank_matrix_norm.index)

    @staticmethod
    def get_similar_users(user_similarity: pd.DataFrame, user: User, head: int, threshold: float):
        if user.username not in user_similarity:
            return pd.DataFrame()
        
        # Filters user that have similarity over the threashold,
        # sorts them based on their similarity score for user in descending order
        # and takes the top n most similar users
        return user_similarity[user_similarity[user.username]>threshold][user.username].sort_values(ascending=False)[:head]
    
    @staticmethod
    def get_similar_user_qbanks(user_qbank_matrix_norm: pd.DataFrame, similar_users: pd.DataFrame, user: User):
        # Qbanks that the target user has rated
        target_user_rated_qbanks = user_qbank_matrix_norm[user_qbank_matrix_norm.index == user.username].dropna(axis=1, how='all')

        # Qbanks that similar users have rated. Remove qbanks that none of the similar users have rated
        similar_user_rated_qbanks = user_qbank_matrix_norm[user_qbank_matrix_norm.index.isin(similar_users.index)].dropna(axis=1, how='all')

        # Remove the rated qbanks by target user from the qbank list
        return similar_user_rated_qbanks.drop(target_user_rated_qbanks.columns,axis=1, errors='ignore')

    @staticmethod
    def get_recommended_qbanks(similar_users: pd.DataFrame, similar_user_qbanks: pd.DataFrame, user: User, head: int):
        # A dictionary to store qbank scores
        qbank_score = {}

        # Loop through qbanks
        for i in similar_user_qbanks.columns:
            # Get the ratings for qbank i
            qbank_rating = similar_user_qbanks[i]
            # Create a variable to store the score
            total = 0
            # Create a variable to store the number of scores
            count = 0

            # Loop through similar users
            for u in similar_users.index:
                # If the qbank has rating
                if not pd.isna(qbank_rating[u]):
                    # Score is the sum of user similarity score multiply by the qbank rating
                    score = similar_users[u] * qbank_rating[u]
                    # Add the score to the total score for the qbank so far
                    total += score
                    # Add 1 to the count
                    count += 1
            # Get the average score for the qbank
            qbank_score[i] = total / count

        # Convert dictionary to pandas dataframe
        qbank_score = pd.DataFrame(qbank_score.items(), columns=['qbank', 'qbank_score'])
                
        # Sort the qbanks by score
        ranked_qbank_score = qbank_score.sort_values(by='qbank_score', ascending=False)
        
        # Get list qbank_ids
        qbank_ids = ranked_qbank_score['qbank'].tolist()

        # Filter out qbanks owned by target user
        for qbank_id in qbank_ids[:]:
            qbank = Qbank.objects.get(qbank_id=qbank_id)
            if not qbank or qbank.owner == user:
                qbank_ids.remove(qbank_id)
        
        # Get top n qbanks
        qbank_ids = qbank_ids[:head]

        # Return queryset
        return Qbank.objects.filter(qbank_id__in=qbank_ids)


class SearchEngine:
    topic_filter_choices = {
        'Data Science': 3,
        'Business': 4,
        'Computer Science': 5,
        'Information Technology': 6,
        'Language Learning': 7,
        'Health': 8,
        'Personal Development': 9,
        'Physical Science and Engineering': 10,
        'Social Sciences': 11,
        'Arts and Humanities': 12,
        'Math and Logic': 13
    }

    @staticmethod
    def get_explore_search_result(user, filter, sort, text):
        filter_choices = {
            '0': 'All',
            '1': 'Recommended',
            '2': 'Users',
            '3': 'Data Science',
            '4': 'Business',
            '5': 'Computer Science',
            '6': 'Information Technology',
            '7': 'Language Learning',
            '8': 'Health',
            '9': 'Personal Development',
            '10': 'Physical Science and Engineering',
            '11': 'Social Sciences',
            '12': 'Arts and Humanities',
            '13': 'Math and Logic'
        }

        sort_choices = {
            '0': 'Trending',
            '1': 'Popular'
        }

        if filter not in filter_choices or sort not in sort_choices:
            raise Http404()
        
        # If it is searching users
        # Filters by Users
        if filter_choices[filter] == 'Users':
            users = User.objects.all()
            if not users:
                return None

            users = UserService.annotate_advanced_metrics(users)

            # Sorts by Trending or Popular
            if sort_choices[sort] == 'Trending':
                users = users.order_by('-followers_count_last_7_days')
            elif sort_choices[sort] == 'Popular':
                users = users.order_by('-followers_count')
            
            # Filters by username
            users = users.filter(Q(username__icontains=text))
            return users

        # If it is searching qbanks
        # Filters by All, Recommended or Topic
        if filter_choices[filter] == 'All':
            qbanks = Qbank.objects.all()
        elif filter_choices[filter] == 'Recommended' and user.is_authenticated:
            qbanks = RecommendationEngine.recommend(user)
        else:
            qbanks = Qbank.objects.filter(topic__name=filter_choices[filter])
        
        if not qbanks:
            return None

        qbanks = QbankService.annotate_advanced_metrics(qbanks)

        # Sorts by Trending or Popular
        if sort_choices[sort] == 'Trending':
            qbanks = qbanks.order_by('-favorites_count_last_7_days')
        elif sort_choices[sort] == 'Popular':
            qbanks = qbanks.order_by('-favorites_count')
        
        # Filters by name and description
        qbanks = qbanks.filter(Q(name__icontains=text) | Q(description__icontains=text))

        return qbanks

    @staticmethod
    def get_vault_search_result(user, filter, sort, text):
        filter_choices = {
            '0': 'All',
            '1': 'Due today',
        }

        sort_choices = {
            '0': 'Name',
            '1': 'Popular'
        }

        if filter not in filter_choices or sort not in sort_choices:
            raise Http404()
        
        # Filters by All or Due today
        if filter_choices[filter] == 'Due today':
            # Gets all cards due today of the user
            card_statuses = CardStatus.objects.filter(
                user=user,
                due_date__lte=timezone.now()
            )

            # Gets all qbanks that have cards due today
            qbanks = Qbank.objects.filter(
                cards__card_status__in=card_statuses
            ).distinct()
        else:
            qbanks = Qbank.objects.all()

        qbanks = QbankService.annotate_basic_metrics(qbanks)

        # Gets the number of cards due today for each qbank
        cards_due_today = {}
        for qbank in qbanks:
            cards_due_today[qbank] = CardStatus.objects.filter(
                user=user,
                card__qbank=qbank,
                due_date__lte=timezone.now()
            ).count()

        # Filters out qbanks that are not favorited by user
        # This is done after annotate so that it counts all the favorites for each qbank before filtering them out
        if filter_choices[filter] == 'All':
            qbanks = qbanks.filter(favorited_by__user=user)

        # Sorts by Name or Popular
        if sort_choices[sort] == 'Name':
            qbanks = qbanks.order_by('name')
        elif sort_choices[sort] == 'Popular':
            qbanks = qbanks.order_by('-favorites_count')
        
        # Filters by name and description
        qbanks = qbanks.filter(Q(name__icontains=text) | Q(description__icontains=text))

        return qbanks, cards_due_today