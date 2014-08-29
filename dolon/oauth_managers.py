import tweepy

from models import OAuthAccessToken

import logging
logging.basicConfig(filename=None, format='%(asctime)-6s: %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

class OAuthManager(object):
    def __init__(self, consumer_key, consumer_secret, callback_url='', **kwargs):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.callback_url = callback_url
        
class TwitterOAuthManager(OAuthManager):
    def __init__(self, *args, **kwargs):
        super(TwitterOAuthManager, self).__init__(*args, **kwargs)
        
        self.auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret, self.callback_url)
    
    def get_access_url(self, callback):
        redirect_url = self.auth.get_authorization_url()
        logger.debug('Redirect URL: {0}'.format(redirect_url))
        
        ptoken = OAuthAccessToken(
                    oauth_token = self.auth.request_token.key,
                    oauth_token_secret = self.auth.request_token.secret,
                    platform='Twitter',
                    )
        ptoken.save()
        
        return redirect_url, ptoken.id
    
    def get_access_token(self, verifier, token):
        
        ptoken = OAuthAccessToken.objects.get(oauth_token=token)
        
        self.auth.set_request_token(    ptoken.oauth_token, 
                                        ptoken.oauth_token_secret   )
        
        self.auth.get_access_token(verifier)
        
        ptoken.oauth_verifier = verifier
        ptoken.oauth_access_token = self.auth.access_token.key
        ptoken.oauth_access_token_secret = self.auth.access_token.secret
        
        api = tweepy.API(self.auth)
        user = api.me()
        ptoken.screen_name = user.screen_name
        ptoken.user_id = user.id
        ptoken.save()
        
        return ptoken.id
        
    
        