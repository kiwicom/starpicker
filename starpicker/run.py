import os
import time
import requests
import itertools
from bs4 import BeautifulSoup
from base64 import b64encode

from .reviews import TrustpilotReview, FacebookRatingReview, FacebookCommentReview, TweetReview

TRUSTPILOT_PAGE_ID = os.getenv('TRUSTPILOT_PAGE_ID')

FACEBOOK_ACCESS_TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN')
FACEBOOK_PAGE_ID = os.getenv('FACEBOOK_PAGE_ID')

TWITTER_APP_KEY = os.getenv('TWITTER_APP_KEY')
TWITTER_APP_SECRET = os.getenv('TWITTER_APP_SECRET')
TWITTER_SEARCH_KEYWORD = os.getenv('TWITTER_SEARCH_KEYWORD')

DEADMANSSNITCH_URL = os.getenv('DEADMANSSNITCH_URL')


def get_trustpilot_reviews():
    response = requests.get('https://www.trustpilot.com/review/{0}'.format(TRUSTPILOT_PAGE_ID))
    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup.findAll('div', 'review'):
        if not tag.find('div', 'review-body'):
            continue
        yield TrustpilotReview(tag)


def get_facebook_ratings():
    response = requests.get(
        'https://graph.facebook.com/v2.4/{0}/ratings'.format(FACEBOOK_PAGE_ID),
        params={'access_token': FACEBOOK_ACCESS_TOKEN, 'fields': 'open_graph_story,review_text,rating,reviewer'}
    )
    for rating in response.json()['data']:
        yield FacebookRatingReview(rating)


def get_facebook_comments():
    response = requests.get(
        'https://graph.facebook.com/v2.4/{0}/feed'.format(FACEBOOK_PAGE_ID),
        params={'access_token': FACEBOOK_ACCESS_TOKEN, 'fields': 'comments'}
    )
    for comment in itertools.chain.from_iterable(post['comments']['data'] for post in response.json()['data'] if 'comments' in post):
        if comment['from']['id'] == FACEBOOK_PAGE_ID:
            continue
        yield FacebookCommentReview(comment)


def get_tweets():
    auth_code = b64encode('{0}:{1}'.format(TWITTER_APP_KEY, TWITTER_APP_SECRET).encode())
    bearer_token = requests.post(
        'https://api.twitter.com/oauth2/token',
        data={'grant_type': 'client_credentials'},
        headers={'Authorization': 'Basic {0}'.format(auth_code.decode())},
    ).json()['access_token']
    for sentiment in (':(', '', ':)'):
        response = requests.get(
            'https://api.twitter.com/1.1/search/tweets.json',
            params={'q': '{0} {1}'.format(TWITTER_SEARCH_KEYWORD, sentiment), 'result_type': 'recent'},
            headers={'Authorization': 'Bearer {0}'.format(bearer_token)},
        )
        for tweet in response.json()['statuses']:
            yield TweetReview(tweet, sentiment)


def main():
    collectors = {
        get_trustpilot_reviews: bool(TRUSTPILOT_PAGE_ID),
        get_facebook_ratings: bool(FACEBOOK_PAGE_ID),
        get_facebook_comments: bool(FACEBOOK_PAGE_ID),
        get_tweets: bool(TWITTER_SEARCH_KEYWORD),
    }
    while True:
        try:
            all_reviews = itertools.chain.from_iterable(
                collector() for collector, enabled in collectors.items() if enabled
            )
            for review in all_reviews:
                if review.is_new:
                    review.send_to_slack()
            if DEADMANSSNITCH_URL:
                requests.get(DEADMANSSNITCH_URL)
        except Exception as ex:
            print(ex)

        time.sleep(os.getenv('CHECK_INTERVAL', 60))

if __name__ == '__main__':
    main()
