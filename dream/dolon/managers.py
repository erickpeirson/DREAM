from django.core.files import File
from models import *
import json
import urllib2
import os
from unidecode import unidecode

from celery import group, chain
from tasks import *
from search_managers import *

import warnings

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

from BeautifulSoup import BeautifulSoup

def spawnRetrieveImages(queryset):
    """
    Generates a set of tasks to retrieve images.
    """
    
    job = group( ( getFile.s(i.url) | storeImage.s(i.id) ) for i in queryset )

    result = job.apply_async()

    return result.id, [ r.id for r in result.results ]    
    
def spawnRetrieveContexts(queryset):
    """
    Generates a group of tasks to retrieve contexts.
    """
    
    job = group( ( getStoreContext.s(i.url, i.id) ) for i in queryset )

    result = job.apply_async()

    return result.id, [ r.id for r in result.results ]       

def spawnSearch(queryevent, **kwargs):
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

    job = group(  ( search.s(qstring, s, min(s+9, end), 
                        queryevent.engine.manager, params, **kwargs) 
                    | processSearch.s(queryevent.id, **kwargs) 
                    | spawnThumbnails.s(queryevent.id, **kwargs)
                    ) for s in xrange(start, end+1, 10) )
                    

    logger.debug('spawnSearch: dispatching jobs')
    result = job.apply_async()
    
    logger.debug('spawnSearch: jobs dispatched')
    
    return result.id, [ r.id for r in result.results ]
    
engineManagers = {
    'GoogleImageSearchManager': GoogleImageSearchManager,
}
