# starpicker

## Summary

A tool that periodically checks sites for feedback about an entity and posts the
findings to Slack. Currently the following sources are supported:

 - trustpilot.com reviews
 - Facebook ratings on a page
 - Facebook comments on a page
 - tweets on Twitter matching a keyword

## Configuration

The following environment variables can be used for configuration:

 - `SLACK_WEBHOOK_URL` (required)
 - `REDIS_URL` (required)
 - `CHECK_INTERVAL` - in seconds
 - `USE_EMOTICONS` - if set, starpicker will prepend messages with :trustpilot:,
   :facebook:, or :twitter: based on the type of the review.

And for setting up specific sources:

### trustpilot.com

 - `TRUSTPILOT_PAGE_ID`

### Facebook

 - `FACEBOOK_ACCESS_TOKEN`
 - `FACEBOOK_PAGE_ID`

### Twitter

 - `TWITTER_APP_KEY`
 - `TWITTER_APP_SECRET`
 - `TWITTER_SEARCH_KEYWORD`
