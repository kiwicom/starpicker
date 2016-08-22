import time
import requests
import logging

from . import config, collectors

LOG = logging.getLogger(__name__)

COLLECTORS = (
    collectors.TrustpilotReviewCollector(),
    collectors.FacebookRatingCollector(),
    collectors.FacebookCommentCollector(),
    collectors.TweetCollector(),
)


def main():
    while True:
        LOG.info('starting review collection')
        try:
            for review in (review for collector in COLLECTORS for review in list(collector.run())):
                if review.is_new:
                    review.send_to_slack()
            if config.DEADMANSSNITCH_URL:
                requests.get(config.DEADMANSSNITCH_URL)
        except:
            LOG.exception('unhandled error')

        LOG.info('review collection done, sleeping for %s seconds', config.CHECK_INTERVAL)
        time.sleep(config.CHECK_INTERVAL)

if __name__ == '__main__':
    main()
