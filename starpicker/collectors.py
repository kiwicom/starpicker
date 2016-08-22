from base64 import b64encode

import logging
import requests
from . import config, reviews

LOG = logging.getLogger(__name__)


class BaseCollector(object):

    url = None
    params = None
    review_class = None
    enabled = False

    def __init__(self):
        LOG.info('%s initiated with URL %s, params %s', self, self.url, self.params)

    def run(self):
        if not self.enabled:
            LOG.debug('%s disabled, skipping', self)
            return
        LOG.debug('starting %s', self)
        try:
            for response, kwargs in self.fetch():
                LOG.debug('got response in %s', self)
                try:
                    for review, inner_kwargs in self.parse(response, **kwargs):
                        LOG.debug('found review in %s', self)
                        try:
                            yield self.review_class(review, **inner_kwargs)
                        except:
                            LOG.exception('error while parsing a %s review, review was %s', self, review)
                except:
                    LOG.exception('error while parsing for %s reviews, response was %s', self, response.text)
        except:
            LOG.exception('error while getting %s response', self)

    def fetch(self):
        LOG.debug('fetching in %s', self)
        yield requests.get(self.url, params=self.params), {}

    def parse(self, response, **kwargs):
        raise NotImplementedError

    def __str__(self):
        return type(self).__name__


class TrustpilotReviewCollector(BaseCollector):

    url = 'https://api.trustpilot.com/v1/business-units/{config.TRUSTPILOT_BUSINESS_ID}/reviews'.format(config=config)
    params = {'apikey': config.TRUSTPILOT_API_KEY}
    review_class = reviews.TrustpilotReview
    enabled = bool(config.TRUSTPILOT_API_KEY) and bool(config.TRUSTPILOT_BUSINESS_ID)

    def parse(self, response, **kwargs):
        for review in response.json()['reviews']:
            yield review, {}

class FacebookRatingCollector(BaseCollector):

    url = 'https://graph.facebook.com/v2.4/{config.FACEBOOK_PAGE_ID}/ratings'.format(config=config)
    params = {'fields': 'open_graph_story,review_text,rating,reviewer', 'access_token': config.FACEBOOK_ACCESS_TOKEN}
    review_class = reviews.FacebookRatingReview
    enabled = bool(config.FACEBOOK_PAGE_ID)

    def parse(self, response, **kwargs):
        for rating in response.json()['data']:
            yield rating, {}


class FacebookCommentCollector(BaseCollector):

    url = 'https://graph.facebook.com/v2.4/{config.FACEBOOK_PAGE_ID}/feed'.format(config=config)
    params = {'fields': 'comments', 'access_token': config.FACEBOOK_ACCESS_TOKEN}
    review_class = reviews.FacebookCommentReview
    enabled = bool(config.FACEBOOK_PAGE_ID)

    def parse(self, response, **kwargs):
        posts = response.json()['data']
        for comment in (comment for post in posts if 'comments' in post for comment in post['comments']['data']):
            try:
                author_id = comment['from']['id']
            except KeyError:
                author_id = None
            if author_id == config.FACEBOOK_PAGE_ID:
                continue
            yield comment, {}


class TweetCollector(BaseCollector):

    url = 'https://api.twitter.com/1.1/search/tweets.json'
    auth_code = b64encode('{0}:{1}'.format(config.TWITTER_APP_KEY, config.TWITTER_APP_SECRET).encode())
    review_class = reviews.TweetReview
    enabled = bool(config.TWITTER_SEARCH_KEYWORD)

    def get_bearer_token(self):
        return requests.post(
            'https://api.twitter.com/oauth2/token', data={'grant_type': 'client_credentials'},
            headers={'Authorization': 'Basic {0}'.format(self.auth_code.decode())},
        ).json()['access_token']

    def fetch(self):
        LOG.debug('fetching in %s', self)
        bearer_token = self.get_bearer_token()
        for sentiment in (':(', '', ':)'):
            yield requests.get(
                self.url,
                params={'q': '{0} {1}'.format(config.TWITTER_SEARCH_KEYWORD, sentiment), 'result_type': 'recent'},
                headers={'Authorization': 'Bearer {0}'.format(bearer_token)},
            ), {'sentiment': sentiment}

    def parse(self, response, **kwargs):
        for tweet in response.json()['statuses']:
            yield tweet, {'sentiment': kwargs['sentiment']}
