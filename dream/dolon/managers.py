from django.core.files import File
from models import QueryItem, QueryResult, Thumbnail, Image, Context
import json
import urllib2
import os
from unidecode import unidecode

from celery import group, chain
from tasks import search, processSearch, spawnThumbnails

import warnings

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

from BeautifulSoup import BeautifulSoup

def spawnSearch(queryevent):
    """
    Executes a series of searches based on the parameters of a 
    :class:`.QueryEvent` and updates it accordingly.
    
    Parameters
    ----------
    queryevent : :class:`.QueryEvent`
        
    Returns
    -------
    result.id : str
        UUID for the Celery search task group.
    """

    if queryevent.dispatched:
        warnings.warn('Attempting to spawnSearch() for QueryEvent that has ' + \
                      ' already been dispatched.', RuntimeWarning)
        return queryevent

    qstring = queryevent.querystring.querystring
    start = queryevent.rangeStart
    end = queryevent.rangeEnd
    engine = engineManagers[queryevent.engine.manager]()

    logger.debug('spawnSearch() for QueryEvent {0},'.format(queryevent.id)    +\
        ' with term "{0}", start: {1}, end: {2},'.format(qstring, start, end) +\
        ' using Engine: {0}'.format(engine.name))

    params = [ p for p in queryevent.engine.parameters ]
    
    # Dispatch a group of search chains to Celery, divided into 10-item pages.
    #
    #   * search() performs the image search for a 10-item page,
    #   |
    #   * processSearch() parses the search results and creates QueryResult 
    #   | and QueryItem instances.
    #   * spawnThumbnails() launches tasks to retrieve and store Thumbnail
    #     instances. 
    #   
    # QueryEvent.id gets passed around so that the various tasks can attach
    #  the resulting objects to it.
    logger.debug('spawnSearch: creating jobs')
    job = group(  ( search.s(qstring, start, start+9, engine, params) 
                    | processSearch.s(queryevent.id) 
                    | spawnThumbnails.s(queryevent.id)
                    ) for start in xrange(start, end, 10) )                   

    logger.debug('spawnSearch: dispatching jobs')
    result = job.apply_async()
    
    logger.debug('spawnSearch: jobs dispatched')
    
    return result.id
    
class BaseSearchManager(object):
    """
    Base class for search managers.
    """
    def __init__(self):
        pass

class GoogleImageSearchManager(BaseSearchManager):
    """
    Search manager for Google Custom Search api.
    """

    endpoint = "https://www.googleapis.com/customsearch/v1?"
    name = 'Google'

    def imageSearch(self, params, query, start=1):
        """
        Performs an image search for ``query`` via the Google Custom Search API.

        Parameters
        ----------
        params : list
            Should contain at least ``apikey`` and ``cx`` parameters.
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


engineManagers = {
    'GoogleImageSearchManager': GoogleImageSearchManager,
}
