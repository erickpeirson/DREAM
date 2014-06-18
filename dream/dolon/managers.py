from django.core.files import File
from models import QueryItem, QueryResult, Thumbnail, Image, Context
import json
import urllib2
import os
from unidecode import unidecode

import warnings

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

from BeautifulSoup import BeautifulSoup

def spawnSearch(queryevent, getThumb=True):
    """
    Executes a series of searches based on the parameters of a 
    :class:`.QueryEvent` and updates it accordingly.
    
    TODO: this should eventually be the point of action for dispatching via
    Celery.
    
    Parameters
    ----------
    queryevent : :class:`.QueryEvent`
    getThumb : bool
        (default: True) If True, retrieves thumbnail image for each item.
    """

    if queryevent.dispatched:
        warnings.warn('Attempting to spawnSearch() for QueryEvent that has already been dispatched.', RuntimeWarning)
        return queryevent

    querystring = queryevent.querystring.querystring
    start = queryevent.rangeStart
    end = queryevent.rangeEnd
    engine = engineManagers[queryevent.engine.manager]()

    logger.debug('spawnSearch() for QueryEvent {0}'.format(queryevent.id) + \
                 ', with term "{0}", start: {1}, end: {2}'
                                               .format(querystring, start, end))
    logger.debug('spawnSearch(): using Engine {0}'.format(engine.name))

    for s in xrange(start, end, 10):
        e = s + 9   # Maximum of 10 results per query.

        P = [ p for p in queryevent.engine.parameters ] # Avoid scoping issue.
        response = engine.imageSearch(P, querystring, start=s)
        result, items = engine.handleResults(response)

        if getThumb:    # Retrieve thumbnails.
            for item in items:
                if item.thumbnail is None:
                    getThumbnail(item)

        queryevent.queryresults.add(result)
        queryevent.save()
        
    logger.debug('spawnSearch(): done.')

    return queryevent

def getThumbnail(queryitem):
    """
    Retrieve a :class:`.Thumbnail` for a :class:`.QueryItem`\.
    
    Parameters
    ----------
    queryitem : :class:`.QueryItem`
    
    Returns
    -------
    success : bool
    """

    try:
        R = ImageRetriever()
        thumbnail = R.retrieveThumbnail(queryitem.thumbnailURL)
        queryitem.thumbnail = thumbnail
        queryitem.save()
    except:
        return False
    return True

def getImage(queryitem):
    """
    Retrieve a :class:`.Image` for a :class:`.QueryItem`\.
    
    Parameters
    ----------
    queryitem : :class:`.QueryItem`
    
    Returns
    -------
    success : bool
    """

    try:
        R = ImageRetriever()
        image = R.retrieveImage(queryitem.url)
        queryitem.image = image
        queryitem.save()
    except:
        return False
    return True

def getContext(queryitem):
    """
    Retrieve a :class:`.Context` for a :class:`.QueryItem`\.
    
    Parameters
    ----------
    queryitem : :class:`.QueryItem`
    
    Returns
    -------
    success : bool
    """

    try:
        R = ImageRetriever()
        context = R.retrieveImage(queryitem.contextURL)
        queryitem.context = context
        queryitem.save()
    except:
        return False
    return True

class ImageRetriever(object):
    temppath = 'tempI'

    def getFile(self, url):
        """
        
        Parameters
        ----------
        url : str
            Location of a file.
        
        Returns
        -------
        filename : str
        file : :class:`.File`
        """

        filename = url.split('/')[-1]
        response = urllib2.urlopen(url)
        
        mime = dict(response.info())['content-type']
        size = dict(response.info())['content-length']
        
        with open(self.temppath, 'wb') as f:
            f.write(response.read())

        self.f = open(self.temppath, 'r')
        file = File(self.f)

        return filename, file, mime, size

    def _cleanup(self):
        self.f.close()
        os.remove(self.temppath)

    def retrieveThumbnail(self, url):
        """
        
        Parameters
        ----------
        url : str
            Location of the thumbnail image.
        
        Returns
        -------
        thumbnail : :class:`.Thumbnail`
        """
        
        filename, imagefile, mime, size = self.getFile(url)

        thumbnail = Thumbnail(  url = url,
                                mime = mime,
                                size = size )
        thumbnail.image.save(filename, imagefile, True)
        thumbnail.save()

        self._cleanup()
        return thumbnail

    def retrieveImage(self, url):
        """
        
        Parameters
        ----------
        url : str
            Location of the image.
            
        Returns
        -------
        image : :class:`.Image`
        """

        filename, imagefile, mime, size = self.getFile(url)

        image = Image(  url = url,
                        mime = mime,
                        size = size )

        image.image.save(filename, imagefile, True)
        image.save()

        self._cleanup()
        return image

    def retrieveContext(self, url):
        """
        
        Parameters
        ----------
        url : str
            Location of the context document.
            
        context : :class:`.Context`
        """

        response = urllib2.urlopen(url).read()
        soup = BeautifulSoup(response)
        text = ' '.join([ p.getText() for p in soup.findAll('p') ])
        title = soup.title.getText()

        context = Context(  url = url,
                            title = title,
                            content = text  )
        context.save()

        return context

class GoogleImageSearchManager(object):
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
        return response.read()

    def handleResults(self, response):
        """
        Extracts information of interest from an :func:`.imageSearch` response.

        Parameters
        ----------
        response : str
            JSON response from :func:`.imageSearch`\.
        
        Returns
        -------
        queryResult : :class:`.QueryResult`
        queryItems : list
            A list of :class:`.QueryItem` instances.
        """

        rjson = json.loads(response)
        
        start = rjson['queries']['request'][0]['startIndex']
        end = start + rjson['queries']['request'][0]['count'] - 1

        queryResult = QueryResult(  rangeStart=start,
                                    rangeEnd=end,
                                    result=response )
        queryResult.save()

        queryItems = []
        for item in rjson['items']:
            # Should only be one QueryItem per URI.
            queryItem = QueryItem.objects.get_or_create(
                            url = item['link'],
                            defaults = {
                                'title': item['title'],
                                'size': item['image']['byteSize'],
                                'height': item['image']['height'],
                                'width': item['image']['width'],
                                'mime': item['mime'],
                                'contextURL': item['image']['contextLink'],
                                'thumbnailURL': item['image']['thumbnailLink']
                            }   )[0]

            queryResult.items.add(queryItem)
            queryItems.append(queryItem)

        queryResult.save()

        return queryResult, queryItems


engineManagers = {
    'GoogleImageSearchManager': GoogleImageSearchManager,
}
