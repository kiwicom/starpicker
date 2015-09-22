import os
import requests
from redis import StrictRedis
from textwrap import dedent
from textblob import TextBlob

R = StrictRedis.from_url(os.environ['REDIS_URL'])
SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']


class BaseReview(object):

    type = None

    SLACK_TEMPLATE = dedent('''
        New {self.type} by {self.author}:

        >>>{self.text}
    ''').strip()


    def __init__(self, review_id, text, rating=None, author=None):
        assert self.type is not None
        self.id = review_id
        self.text = text
        self._rating = rating
        self._author = author
        self.is_new = R.sadd('starpicker:seen_review_ids', self.redis_key) == 1

    @property
    def redis_key(self):
        return '{self.__class__.__name__}:{self.id}'.format(self=self)

    @property
    def author(self):
        return self._author

    @property
    def rating(self):
        if self._rating:
            return self._rating
        elif len(self.text) > 3:
            blob = TextBlob(self.text)
            if blob.detect_language() == 'en':
                return round(min(max(blob.sentiment.polarity, -0.5), 0.5) * 4 + 3)

    def send_to_slack(self):
        color_map = {1: 'danger', 2: 'warning', 3: 'warning', 5: 'good'}

        body = {
            'username': 'starpicker',
            'attachments': [
                {
                    'fallback': self.SLACK_TEMPLATE.format(self=self),
                    'pretext': self.SLACK_TEMPLATE.format(self=self).split('\n')[0],
                    'text': self.text,
                    'color': color_map.get(self.rating),
                    'title': '{self.type} #{self.id}'.format(self=self),
                    'title_link': self.url,
                    'fields': [
                        {
                            'title': 'Author',
                            'value': self.author,
                            'short': True,
                        },
                        {
                            'title': 'Rating',
                            'value': self.rating or '?',
                            'short': True,
                        },
                    ]
                }
            ]
        }

        requests.post(SLACK_WEBHOOK_URL, json=body)


class TrustpilotReview(BaseReview):

    type = 'Trustpilot review'

    def __init__(self, tag):
        body = '\n\n'.join(
            tag.strip()
            for tag in tag.find('div', 'review-body').contents
            if isinstance(tag, str)
        )
        rating = int(tag.find('meta', itemprop='ratingValue')['content'])
        author = tag.find('div', 'user-review-name').find('span', itemprop='name').text
        return super(TrustpilotReview, self).__init__(tag['data-reviewmid'], body, rating, author)

    @property
    def url(self):
        return 'https://www.trustpilot.com/review/skypicker.com/{self.id}'.format(self=self)


class FacebookRatingReview(BaseReview):

    type = 'Facebook review'

    def __init__(self, rating):
        super(FacebookRatingReview, self).__init__(
            rating['open_graph_story']['id'],
            rating.get('review_text', ''),
            rating['rating'],
            rating['reviewer']['name'],
        )

    @property
    def url(self):
        return 'https://www.facebook.com/{self.id}'.format(self=self)


class FacebookCommentReview(BaseReview):

    type = 'Facebook comment'

    def __init__(self, comment):
        return super(FacebookCommentReview, self).__init__(
            comment['id'], comment['message'], author=comment['from']['name']
        )

    @property
    def url(self):
        return 'https://www.facebook.com/{0}'.format(self.id.split('_')[0])


class TweetReview(BaseReview):

    sentiment_map = {':(': 1, '': None, ':)': 5}
    type = 'tweet'

    def __init__(self, tweet, sentiment):
        return super(TweetReview, self).__init__(
            tweet['id'], tweet['text'], self.sentiment_map[sentiment], tweet['user']
        )

    @property
    def url(self):
        return 'https://www.twitter.com/{self._author[screen_name]}/status/{self.id}'.format(self=self)

    @property
    def author(self):
        return self._author['name']
