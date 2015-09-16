import os
import math
import requests
from redis import StrictRedis
from textwrap import dedent
from textblob import TextBlob

R = StrictRedis.from_url(os.environ['REDIS_URL'])
SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']


class Review(object):

    SLACK_TEMPLATE = dedent('''
        New {self.type}:

        >>>{self.text}
    ''').strip()


    def __init__(self, review_type, review_id, text, rating=None):
        self.type = review_type
        self.id = review_id
        self.text = text
        self.rating = rating
        self.is_new = R.sadd('starpicker:seen_review_ids', self.redis_key) == 1

    @classmethod
    def from_trustpilot(cls, tag):
        body = '\n\n'.join(
            tag.strip()
            for tag in tag.find('div', 'review-body').contents
            if isinstance(tag, str)
        )
        rating = int(tag.find('meta', itemprop='ratingValue')['content'])
        return cls('trustpilot.com review', tag['data-reviewmid'], body, rating)

    @classmethod
    def from_facebook_rating(cls, rating):
        return cls('Facebook review', rating['created_time'], rating['review_text'], rating['rating'])

    @classmethod
    def from_facebook_comment(cls, comment):
        return cls('Facebook comment', comment['id'], comment['message'])

    @classmethod
    def from_tweet(cls, tweet, sentiment):
        sentiment_map = {':(': 1, '': None, ':)': 5}
        return cls('tweet', tweet['id'], tweet['text'], sentiment_map[sentiment])

    @property
    def redis_key(self):
        return '{self.type}:{self.id}'.format(self=self)

    @property
    def sentiment(self):
        blob = TextBlob(self.text)
        if blob.detect_language() == 'en':
            return math.round(blob.sentiment[0] * 2 + 3)

    def send_to_slack(self):
        if self.rating is None:
            self.rating = self.sentiment

        color_map = {1: 'danger', 2: 'warning', 3: 'warning', 5: 'good'}

        body = {
            'username': 'starpicker',
            'attachments': [
                {
                    'fallback': self.SLACK_TEMPLATE.format(self=self),
                    'pretext': self.SLACK_TEMPLATE.format(self=self).split('\n')[0],
                    'text': self.text,
                    'color': color_map.get(self.rating),
                }
            ]
        }

        requests.post(SLACK_WEBHOOK_URL, json=body)
