from django.core.files import File
from models import *
import json
import urllib2
import os
from unidecode import unidecode
import xml.etree.ElementTree as ET
import time

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

class MediaTypeException(Exception):
    """
    Raised when a :class:`.BaseSearchManager` encounters a mismatch between
    declared and actual media types.
    """

    pass

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
    
    endpoint = 'https://archive.org/advancedsearch.php?'
    details_endpoint = 'https://archive.org/details/'
    name = 'Internet Archive'
    
    audio_formats = ['mp3', 'wav', 'flac', 'ogg' ]
    video_formats = ['mp4', 'ogv', 'avi', 'mov']
    
    def search(self, params, query, start=1, end=10):
        """
        Perform a search of the Internet Archive.
        """
        rows = (end - start) + 1
        
        logger.debug('search for {0}, start: {1}, end: {2}, rows: {3}'
                                            .format(query, start, end, rows))

        params += [ "q={0}".format(urllib2.quote(query)),
                    "rows={0}".format(rows),
                    "start={0}".format(start),                    
                    "indent=yes",
                    "output=json"   ]
                    
        request = self.endpoint + "&".join(params)
        logger.debug('request: {0}'.format(request))
        
        response = urllib2.urlopen(request)
        
        rcontent = response.read()
        if type(rcontent) is unicode:
            rcontent = unidecode(rcontent)


        return self._handleResponse(rcontent)
    
    def _parseFilemeta(self, baseurl, filemeta_content, mtype):
        # e.g. see http://ia600309.us.archive.org/31/items/Insight_101214/Insight_101214_files.xml
        root = ET.fromstring(filemeta_content)

        # Only accept known types.
        if mtype == 'audio': 
            known = self.audio_formats
            alt = self.video_formats
            alttype = 'video'
        elif mtype == 'video':
            known = self.video_formats
            alt = self.audio_formats
            alttype = 'audio'

        files = []
        thumbs = []
        mtype_match = False
        alttype_match = False
        for child in root:
            filename = child.attrib['name']
            ext = filename.split('.')[-1].lower()
            if ext in known:   
                files.append( ''.join([ baseurl, filename ]) )
                mtype_match = True
            elif ext in alt:
                alttype_match = True
                
            if child.find('format').text == 'Thumbnail':
                thumbs.append(''.join([ baseurl, filename ]))
            
        # Sometimes mtype is wrong in the metadata record.
        if not mtype_match and alttype_match:   # Declared mtype is incorrect.
            logger.debug('No {0} content, but found {1} content'
                                                        .format(mtype, alttype))
            raise MediaTypeException('No {0} content, but found {1} content'
                                                        .format(mtype, alttype))  

        return files, thumbs
    
    def _parseMetacontent(self, baseurl, meta_content):
        # e.g. see http://ia600309.us.archive.org/31/items/Insight_101214/Insight_101214_meta.xml
        root = ET.fromstring(meta_content)
        
        creator = ''    # Default values.
        description = ''
        for child in root:
            if child.tag == 'publicdate':   # TODO: want other dates?
                date_published = datetime.strptime(
                                    child.text, '%Y-%m-%d %H:%M:%S' )
            if child.tag == 'uploader':
                creator = child.text
            if child.tag == 'description':
                description = unidecode(unicode(child.text))
            
        return date_published, creator, description
    
    def _getContext(self, identifier):
        # Use this as the context url.
        contextURL = self.details_endpoint + identifier
        request = contextURL + '&output=json'

        logger.debug('request: {0}'.format(request))

        # Get JSON content describing item.
        content = urllib2.urlopen(request).read()
        rjson = json.loads(content)
        
        server = rjson['server']
        dir = rjson['dir']
        baseurl = ''.join(['http://', server, dir, '/' ])
        
        return contextURL, baseurl
    
    def _getDetails(self, identifier, mtype):
        """
        Get context url, pub date, creator, and description for
        an audio item.
        """
        
        contextURL, baseurl = self._getContext(identifier)
        
        # Get URLs for all audio files.
        filemeta = ''.join([baseurl, identifier, '_files.xml'])        
        filemeta_content = urllib2.urlopen(filemeta).read()
        files, thumbs = self._parseFilemeta(baseurl, filemeta_content, mtype)
        
        # Get metadata about item: creator, date_published
        metaurl = ''.join([baseurl, identifier, '_meta.xml'])        
        meta_content = urllib2.urlopen(metaurl).read()
        date_pub, creator, desc = self._parseMetacontent(baseurl, meta_content)
                
        return contextURL, date_pub, creator, desc, files, thumbs

    
    def _handleResponse(self, response=None):
    
        rjson = json.loads(response)

        N = len(rjson['response']['docs'])
        logger.debug('response contains {0} items'.format(N))
        
        items = []
        for item in rjson['response']['docs']:
            # Don't make calls too rapidly.
            time.sleep(0.5) # TODO: figure out a more robust pattern here.
            
            # Movies and audio are handled differently.
            #   Video files (movies)...
            if item['mediatype'] == 'movies':
                mtype = 'video'
                alttype = 'audio'
            #   Audio files...
            elif item['mediatype'] == 'audio': 
                mtype = 'audio'
                alttype = 'video'

            try:    # Catch cases where declared mtype is incorrect.
                md = self._getDetails(item['identifier'], mtype)
            except MediaTypeException:
                md = self._getDetails(item['identifier'], alttype)
                mtype = alttype
            contextURL, date_pub, creator, desc, files, thumbs = md
                
            if item['mediatype'] == 'texts': continue # TODO: handle texts?

            items.append({
                'title': item['title'],
                'type': mtype,
                'url': contextURL,
                'contextURL': contextURL,
                'date': date_pub,
                'creator': creator,
                'description': desc,
                'thumbnailURL': thumbs,
                'files': files,
                 })
                 
        start = int(rjson['response']['start'])
        end = int(rjson['responseHeader']['params']['rows']) + start
        result = {  'items': items, 
                    'start': start, 
                    'end': end  }
        
        return result, rjson

class GoogleImageSearchManager(BaseSearchManager):
    """
    Search manager for Google Custom Search api.
    """

    endpoint = "https://www.googleapis.com/customsearch/v1?"
    name = 'Google'

    def search(self, params, query, start=1, end=10):
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
        
        logger.debug('params: {0}'.format(params))
        
        params += [ "q={0}".format(urllib2.quote(query)),
                    "start={0}".format(start),
                    "num={0}".format((end - start) + 1),
                    "searchType=image"  ]

        request = self.endpoint + "&".join(params)
        logger.debug('request: {0}'.format(request))
        
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
                    'title': unidecode(item['title']),
                    'size': item['image']['byteSize'],
                    'height': item['image']['height'],
                    'width': item['image']['width'],
                    'mime': item['mime'],
                    'contextURL': item['image']['contextLink'],
                    'creator': '',
                    'thumbnailURL': [item['image']['thumbnailLink'],]
                }
            result['items'].append(i)

        return result, rjson
        
