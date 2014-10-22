from dolon.search_managers import BaseSearchManager
from dolon.models import BaseQueryEvent
from .models import GoogleQueryEvent
import urllib2

class GoogleSearchManager(BaseSearchManager):
    """
    Search manager for Google Custom Search api.
    """

    queryevent_class = GoogleQueryEvent
    endpoint = "https://www.googleapis.com/customsearch/v1?"
    name = 'Google'
    max_results = 100
    max_pagesize = 10
    month_limit = 30000
    day_limit = 1000
    second_limit = 2
    
    
    
    parameters = (
        'exactTerms_id', 'orTerms', 'highRange', 'num', 'cr','imgType','gl','q',
        'relatedSite','searchType', 'fileType', 'imgDominantColor','start',
        'lr','siteSearch', 'excludeTerms_id','cref','sort','hq','c2coff',
        'googlehost','safe','exactTerms','hl','lowRange','imgSize',
        'imgColorType','rights','excludeTerms','filter','linkSite',
        'siteSearchFilter','dateRestrict'
        )
                    
    def validate_num(self, num):
        """
        Google only allows up to 10 results per request, and 100 results per
        query (10 pages of 10 results each).
        """
        
        assert num <= self.max_pagesize
        if 'start' in self.pdata:
            assert self.pdata['start'] + num <= self.max_results
        
    def validate_start(self, start):
        """
        Google only allows 100 results per query (10 pages of 10 results each).
        """
        
        assert 1 <= start <= self.max_results
    
        
#        query = queryevent.querystring.querystring
#        _params = [ p for p in queryevent.engine.parameters ]
#        _start = queryevent.rangeStart
#        _end = queryevent.rangeEnd
#        
#        
#        pagesize = ( queryevent.engine.pagesize or 10 )
#        
#        results = []
#        for i in xrange(_start, _end, pagesize):
#            start = i
#            end = min(start + pagesize - 1, _end)
#            
#            params = _params + [ "q={0}".format(urllib2.quote(query)),
#                                 "start={0}".format(start),
#                                 "num={0}".format((end - start) + 1),
#                                 "searchType=image"  ]
#
#            request = self.endpoint + "&".join(params)
#            logger.debug('request: {0}'.format(request))
#            
#            response = urllib2.urlopen(request)
#            results.append(self._handleResponse(response.read()))

#        return results

    def _handleResponse(self, response):
        """
        Extracts information of interest from an :func:`.imageSearch` response.

        Parameters
        ----------
        response : str
            JSON response from :func:`.imageSearch`\.
        
        Returns
        -------
        result : dict
            Limited results, amenable to :class:`.QueryItem`\.
        rjson : dict
            Full parsed JSON response.
        """
        
        rjson = json.loads(response)

        result = {}
        
        result['start'] = rjson['queries']['request'][0]['startIndex']
        result['end'] = result['start'] + rjson['queries']['request'][0]['count'] - 1        
        
        result['items'] = []
        for item in rjson['items']:
            i = {
                    'type': 'image',
                    'url': item['link'],
                    'title': unidecode(item['title']),
                    'size': item['image']['byteSize'],
                    'height': item['image']['height'],
                    'width': item['image']['width'],
                    'mime': item['mime'],
                    'contextURL': item['image']['contextLink'],
                    'creator': '',
                    'thumbnailURL': [item['image']['thumbnailLink'],],
                    'files': [item['link']],
                }
            result['items'].append(i)

        return result, rjson
