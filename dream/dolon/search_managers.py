from django.core.files import File
from models import *
import json
import urllib2
import os
from unidecode import unidecode

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

class BaseSearchManager(object):
    """
    Base class for search managers.
    """
    def __init__(self):
        pass
        
class InternetArchiveManager(BaseSearchManager):
    """
    Search manager for Internet Archive.
    
    Documentation can be found `here <https://archive.org/help/json.php>`_.
    """
    
    def search(self, params, query, start, end):
        """
        Perform a search of the Internet Archive.
        """
        
        #https://archive.org/advancedsearch.php?
        
        # q=%22dream+act%22
        # &fl%5B%5D=collection&fl%5B%5D=creator&fl%5B%5D=date&fl%5B%5D=description&fl%5B%5D=format&fl%5B%5D=identifier&fl%5B%5D=imagecount&fl%5B%5D=mediatype&fl%5B%5D=publisher&fl%5B%5D=rights&fl%5B%5D=source&fl%5B%5D=subject&fl%5B%5D=title&fl%5B%5D=type
        # &sort%5B%5D=&sort%5B%5D=&sort%5B%5D=
        # &rows=50
        # &page=2
        # &indent=yes
        # &output=json
        
        pass
    
    

class GoogleImageSearchManager(BaseSearchManager):
    """
    Search manager for Google Custom Search api.
    """

    endpoint = "https://www.googleapis.com/customsearch/v1?"
    name = 'Google'

    def imageSearch(self, params, query, start=1, end=10):
        """
        Performs an image search for ``query`` via the Google Custom Search API.

        Parameters
        ----------
        params : list
            Should contain at least ``key`` and ``cx`` parameters.
        query : str
            Search query.
        start : int
            (default: 1) Start item.

        Returns
        -------
        response : string
            JSON response.
        """
        
        logger.debug('imageSearch() with params {0}'.format(params))
        
        params += [ "q={0}".format(urllib2.quote(query)),
                    "start={0}".format(start),
                    "num={0}".format((end - start) + 1),
                    "searchType=image"  ]

        request = self.endpoint + "&".join(params)
        logger.debug('imageSearch(): request: {0}'.format(request))
        
        response = urllib2.urlopen(request)
        
        return self._handleResponse(response.read())

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
                    'title': item['title'],
                    'size': item['image']['byteSize'],
                    'height': item['image']['height'],
                    'width': item['image']['width'],
                    'mime': item['mime'],
                    'contextURL': item['image']['contextLink'],
                    'thumbnailURL': item['image']['thumbnailLink']      
                }
            result['items'].append(i)

        return result, rjson
        
