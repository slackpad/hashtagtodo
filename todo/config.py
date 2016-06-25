import os

from authomatic.providers import oauth2


# Your registered OAuth information gets filled in here.
AUTH_SERVICES = {
    'google': {
        'id': 1,
        'class_': oauth2.Google,
        'consumer_key': 'TODO',
        'consumer_secret': 'TODO',
        'scope': oauth2.Google.user_info_scope + ['https://www.googleapis.com/auth/calendar'],
        'offline': True,
    }
}

# Generate secure values for use in encrypting cookies.
AUTH_SECRET = 'TODO'
COOKIE_SECRET = 'TODO'

# The ROOT_URL should be set to the full, public path to your instance
# (eg. https://www.hashtagtodo.com).
ROOT_URL = 'TODO'
USER_AGENT = 'hashtagtodo-v1'

# Set emails used for automation.
EMAILS = {
    'alerts': 'HashtagTodo Alerts <TODO>',
    'support': 'HashtagTodo Support <TODO>',
}

def is_prod():
    return not os.environ['SERVER_SOFTWARE'].startswith('Development')
