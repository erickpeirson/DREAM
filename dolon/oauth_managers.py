import tweepy

from models import OAuthAccessToken, SocialPlatform

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
        
        self.auth = tweepy.OAuthHandler(    self.consumer_key, 
                                            self.consumer_secret, 
                                            self.callback_url   )
    
    def get_access_url(self, callback):
        """
        Generates an access URL to which the user should be redirected in order
        to authorize Dolon.
        
        Parameters
        ----------
        callback : str
            Callback URL to which the user should be redirected after 
            authorizing Dolon. That view will receive a verifier, which is then
            used to obtain an access token.
        
        Returns
        -------
        redirect_url : str
            The URL to which the user should be redirected in order to authorize
            Dolon.
        ptoken.id : int
            ID of a :class:`.OAuthAccessToken` containing the original request
            token.
        """
        
        redirect_url = self.auth.get_authorization_url()
        logger.debug('Redirect URL: {0}'.format(redirect_url))
        
        # We must create an OAuthAccessToken here because we need the request
        #  tokens used when the authorization URL was generated.
        
        platform = SocialPlatform.objects.get(name='Twitter')
        ptoken = OAuthAccessToken(
                    oauth_token = self.auth.request_token.key,
                    oauth_token_secret = self.auth.request_token.secret,
                    platform=platform,
                    )
        ptoken.save()
        
        return redirect_url, ptoken.id
    
    def get_access_token(self, verifier, token):
        """
        Handles the verifier returned by Twitter to the callback url after the
        user authorizes Dolon. The verifier is used to retrieve an access token,
        which is added to the :class:`.OAuthAccessToken` created by
        :meth:`.get_access_url`\.
        
        Parameters
        ----------
        verifier : str
            Verifier returned by Twitter via the callback.
        token : int
            ID of an :class:`.OAuthAccessToken`\.
            
        Returns
        -------
        ptoken.id : int
            The ID of the updated :class:`.OAuthAccessToken`\. Should be 
            identical to the provided ``token``.
        """
        
        # We need the original request token in order to retrieve the
        #  authorization token.
        ptoken = OAuthAccessToken.objects.get(oauth_token=token)
        self.auth.set_request_token(    ptoken.oauth_token, 
                                        ptoken.oauth_token_secret   )
        
        # Now we get the access token using the verifier.
        self.auth.get_access_token(verifier)
        
        # ...and update the OAuthAccessToken object.
        ptoken.oauth_verifier = verifier
        ptoken.oauth_access_token = self.auth.access_token.key
        ptoken.oauth_access_token_secret = self.auth.access_token.secret
        
        api = tweepy.API(self.auth)  # Get details about the user who authorized
        user = api.me()              #  Dolon.
        ptoken.screen_name = user.screen_name
        ptoken.user_id = user.id
        ptoken.save()
        
        # Clean up any unused OAuthAccessToken objects.
        tokens = OAuthAccessToken.objects.all()
        for token in tokens:
            if token.oauth_access_token is None:
                token.delete()
        
        return ptoken.id
        
