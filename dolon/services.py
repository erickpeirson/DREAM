import urllib2
import json

class DiffBotManager(object):
    article_endpoint = 'http://api.diffbot.com/v3/article'
    
    def __init__(self, token=None):
        self.token = token
        
    def prep_request(self, type, url, opt_params=[]):
        params = [
            'url={0}'.format(url),
            'type={0}'.format(type),
            ] + opt_params
        
        return params

    def get_article(self, url):
        params = self.prep_request('article', url)
        article = self.get(params)
        return article

    def get(self, params):
            
        if self.token is None:  # Must have a token.
            raise ValueError('DiffBot API call requires valid token.')
            
        params += ['token={0}'.format(self.token) ]

        request = '{0}?{1}'.format(self.article_endpoint, '&'.join(params))
        response = urllib2.urlopen(request)
        
        encoding=response.headers['content-type'].split('charset=')[-1]
        ucontent = unicode(response.read(), encoding)
        
        result = json.loads(ucontent, "ISO-8859-1")
        
        return result
        

        