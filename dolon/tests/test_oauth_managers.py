from django.test import TestCase

from ..oauth_managers import *
from ..models import OAuthAccessToken
from dream.settings import TWITTER_KEY, TWITTER_SECRET

class TestTwitterOAuthManager(TestCase):
    def setUp(self):
        self.manager = TwitterOAuthManager(
                            consumer_key=TWITTER_KEY,
                            consumer_secret=TWITTER_SECRET
                            )
        
    def test_get_access_url(self):
        url, ptoken_id = self.manager.get_access_url()
        self.assertIsInstance(url, str)
        self.assertGreater(len(url), 0)
        
        
        ptoken = OAuthAccessToken.objects.get(pk=ptoken_id)
        self.assertNotEqual(ptoken.oauth_token, None)
        self.assertNotEqual(ptoken.oauth_token_secret, None)
        
    