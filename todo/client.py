import datetime
import httplib2
import json
import oauth2client.client
import os
import uritemplate

from apiclient.discovery import _add_query_parameter, build_from_document
from apiclient.discovery import DISCOVERY_URI
from apiclient.errors import HttpError, InvalidJsonError
from authomatic import Authomatic
from google.appengine.ext import ndb
from todo.config import AUTH_SECRET, AUTH_SERVICES, USER_AGENT


AUTHOMATIC = Authomatic(AUTH_SERVICES, AUTH_SECRET)
DISCOVERY_EXPIRY = datetime.timedelta(hours=24)
TOKEN_REFRESH_SECONDS = 60 * 4

def retrieve_discovery_doc(serviceName, version,
                           discoveryServiceUrl=DISCOVERY_URI):
    params = {'api': serviceName, 'apiVersion': version}
    requested_url = uritemplate.expand(discoveryServiceUrl, params)

    # REMOTE_ADDR is defined by the CGI spec [RFC3875] as the environment
    # variable that contains the network address of the client sending the
    # request. If it exists then add that to the request for the discovery
    # document to avoid exceeding the quota on discovery requests.
    if 'REMOTE_ADDR' in os.environ:
        requested_url = _add_query_parameter(requested_url, 'userIp',
                                             os.environ['REMOTE_ADDR'])

    http = httplib2.Http()
    resp, content = http.request(requested_url)
    if resp.status >= 400:
        raise HttpError(resp, content, uri=requested_url)

    try:
        service = json.loads(content)
    except ValueError:
        raise InvalidJsonError(
            'Bad JSON: %s from %s.' % (content, requested_url))

    # We return content instead of the JSON deserialized service because
    # build_from_document() consumes a string rather than a dictionary.
    return content

class DiscoveryDocument(ndb.Model):
  document = ndb.StringProperty(required=True, indexed=False)
  updated = ndb.DateTimeProperty(auto_now=True, indexed=False)

  @property
  def expired(self):
      now = datetime.datetime.utcnow()
      return now - self.updated > DISCOVERY_EXPIRY

  @classmethod
  def build(cls, serviceName, version, **kwargs):
    discoveryServiceUrl = kwargs.pop('discoveryServiceUrl', DISCOVERY_URI)
    key = ndb.Key(cls, serviceName, cls, version, cls, discoveryServiceUrl)
    discovery_doc = key.get()

    if discovery_doc is None or discovery_doc.expired:
        # Note that we DO NOT pass the incoming http object here, we use the
        # default so that we retrieve the doc without any user authentication.
        document = retrieve_discovery_doc(
            serviceName, version, discoveryServiceUrl=discoveryServiceUrl)
        discovery_doc = cls(key=key, document=document)
        discovery_doc.put()

    return build_from_document(discovery_doc.document, **kwargs)

def make_client(user):
    credentials = AUTHOMATIC.credentials(user.credentials)

    # The token refresh will be a no-op if it's not due to expire soon.
    orig_token = credentials.token
    credentials.refresh(soon=TOKEN_REFRESH_SECONDS)
    if credentials.token != orig_token:
        user.credentials = credentials.serialize()
        user.put()

    # TODO - The code from here down will only work for Google clients. We
    # should generalize a bit.

    # The refresh here should never be used, but we add it here just so
    # requests will go through if we get into a weird state.
    oauth_credentials = oauth2client.client.OAuth2Credentials(
        access_token=credentials.token,
        client_id=credentials.consumer_key,
        client_secret=credentials.consumer_secret,
        refresh_token=credentials.refresh_token,
        token_expiry=credentials.expiration_date,
        token_uri=credentials.provider_class.access_token_url,
        user_agent=USER_AGENT)

    http = httplib2.Http()
    http = oauth_credentials.authorize(http)
    return DiscoveryDocument.build('calendar', 'v3', http=http)
