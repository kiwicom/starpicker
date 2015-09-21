import os
import time
import requests
import itertools
from bs4 import BeautifulSoup
from base64 import b64encode

from . import Review

TRUSTPILOT_PAGE_ID = os.getenv('TRUSTPILOT_PAGE_ID')

FACEBOOK_ACCESS_TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN')
FACEBOOK_PAGE_ID = os.getenv('FACEBOOK_PAGE_ID')

TWITTER_APP_KEY = os.getenv('TWITTER_APP_KEY')
TWITTER_APP_SECRET = os.getenv('TWITTER_APP_SECRET')
TWITTER_SEARCH_KEYWORD = os.getenv('TWITTER_SEARCH_KEYWORD')


def get_trustpilot_reviews():
    response = requests.get('https://www.trustpilot.com/review/{0}'.format(TRUSTPILOT_PAGE_ID))
    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup.findAll('div', 'review'):
        if not tag.find('div', 'review-body'):
            continue
        yield Review.from_trustpilot(tag)


def get_facebook_ratings():
    response = requests.get(
        'https://graph.facebook.com/v2.4/{0}/ratings'.format(FACEBOOK_PAGE_ID),
        params={'access_token': FACEBOOK_ACCESS_TOKEN, 'fields': 'created_time,review_text,rating'}
    )
    for rating in response.json()['data']:
        if 'review_text' not in rating:
            continue
        yield Review.from_facebook_rating(rating)


def get_facebook_comments():
    response = requests.get(
        'https://graph.facebook.com/v2.4/{0}'.format(FACEBOOK_PAGE_ID),
        params={'access_token': FACEBOOK_ACCESS_TOKEN, 'fields': 'feed{comments}'}
    )
    for comment in itertools.chain.from_iterable(post['comments']['data'] for post in response.json()['feed']['data'] if 'comments' in post):
        if comment['from']['id'] == FACEBOOK_PAGE_ID:
            continue
        yield Review.from_facebook_comment(comment)


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
            yield Review.from_tweet(tweet, sentiment)


def main():
    collectors = {
        get_trustpilot_reviews: bool(TRUSTPILOT_PAGE_ID),
        get_facebook_ratings: bool(FACEBOOK_PAGE_ID),
        get_facebook_comments: bool(FACEBOOK_PAGE_ID),
        get_tweets: bool(TWITTER_SEARCH_KEYWORD),
    }
    while True:
        all_reviews = itertools.chain.from_iterable(
            collector() for collector, enabled in collectors.items() if enabled
        )
        for review in all_reviews:
            if review.is_new:
                review.send_to_slack()

        time.sleep(os.getenv('CHECK_INTERVAL', 60))

if __name__ == '__main__':
    main()
