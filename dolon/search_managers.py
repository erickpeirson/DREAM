from django.core.files import File
from models import *
from util import localize_date, localize_datetime
import json
import urllib2
import os
from unidecode import unidecode
import xml.etree.ElementTree as ET
import time
import math
import tweepy
import facebook
import tempfile
import cPickle as pickle
from dream import settings

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
    def __init__(self, *args, **kwargs):
        pass
        
class FacebookManager(BaseSearchManager):
    base = "https://graph.facebook.com"
    
    def search(self, queryevent_id):
        try:
            results = []
            
            queryevent = QueryEvent.objects.get(pk=queryevent_id)
            access_token = queryevent.engine.oauth_token.oauth_access_token
            
            self.api = facebook.GraphAPI(access_token)
            
            _start = queryevent.rangeStart
            _end = queryevent.rangeEnd
            Nitems = min(_end - _start + 1, 1500)
            
            if queryevent.search_by == 'UR':  
                user_id = queryevent.user.user_id
                feed = self.api.get_connections(str(user_id), "home")
                logger.debug(feed)
        except Exception as E:
            logger.debug(E)
            return 'ERROR'
        return results                

class TwitterManager(BaseSearchManager):
    def __init__(self, *args, **kwargs):        
        self.auth = tweepy.OAuthHandler(settings.TWITTER_KEY,
                                        settings.TWITTER_SECRET)

    def search(self, queryevent_id):
        try:
            results = []
            
            queryevent = QueryEvent.objects.get(pk=queryevent_id)
            
            # Initialize Twitter API connection.    
            access_token = queryevent.engine.oauth_token.oauth_access_token
            access_secret = queryevent.engine.oauth_token.oauth_access_token_secret
            self.auth.set_access_token(  access_token, access_secret )
            self.api = tweepy.API(self.auth)    

            _start = queryevent.rangeStart
            _end = queryevent.rangeEnd
            Nitems = min(_end - _start + 1, 1500)

            # String search.
            if queryevent.search_by == 'ST':    
                q = queryevent.querystring.querystring
                cursor = tweepy.Cursor(self.api.search, q, show_user=True)
                
            # User timeline search.
            elif queryevent.search_by == 'UR':  
                user_id = queryevent.user.user_id
                cursor = tweepy.Cursor(self.api.user_timeline, user_id=user_id)

            # Tag search.
            elif queryevent.search_by == 'TG':
                q = queryevent.tag.string
                if q[0] != '#': q = '#' + q     # Prepend hash if not present.
                cursor = tweepy.Cursor(self.api.search, q, show_user=True)
                
            tweets = [ tweet for tweet in cursor.items(Nitems) ]
                               
            start = queryevent.rangeStart
            end = queryevent.rangeEnd
            result, response = self._handle_tweets(tweets, start, end)
            results.append((result,response))                
                
        except Exception as E:
            logger.debug(E)
            return 'ERROR'
        return results
        
    def _handle_tweets(self, tweets, start, end):
        items = []
        for tweet in tweets:
            tweet_id = tweet.id                     # int
            creationdate = localize_datetime(tweet.created_at, 'UTC')
            screen_name = tweet.user.screen_name    # unicode
            user_id = tweet.user.id                 # int

            tweet_url = 'http://twitter.com/{0}/status/{1}'.format(
                                                        screen_name, tweet_id )
            tweet_title = 'Tweet by {0} at {1} with id {2}'.format(
                                            screen_name, creationdate, tweet_id)

            tweet_content = tweet.text.encode('utf-8')
            
            # Generate a SocialUser
            self._handle_user(user_id, screen_name)
            
            # Pickle tweet and store as an original_file Text.
            text,created = Text.objects.get_or_create(url=tweet_url)
            if created:
                filename = 'tweet_{0}_{1}'.format( screen_name, tweet_id    )
                f_,fpath = tempfile.mkstemp()
                with open(fpath, 'w') as f:
                    pickle.dump(tweet, f)
                with open(fpath, 'r') as f:
                    file = File(f)
                    text.text_file.save(filename, file, True)
                    text.size = f.tell()
                    text.mime = 'application/octet-stream'
                    text.save()
            text_url = text.url
            tweet_size = text.size
            
            item = {
                'url': tweet_url,
                'title': tweet_title,
                'contextURL': tweet_url,
                'type': 'texts',
                'files': [ tweet_url ],
                'length': len(tweet_content),
                'size': tweet_size,
                'creator': 'Twitter:{0}:{1}'.format(user_id, screen_name),
                'retrieved': True,
                'contents': tweet_content,
                'creationDate': creationdate,
                'context': {
                    'use_diffbot': False,
                    'content': tweet_content,
                    'retrieved': True,
                    'title': tweet_title,
                    'publicationDate': creationdate,
                    'author':  'Twitter:{0}:{1}'.format(user_id, screen_name),
                    'text_content': tweet_content,
                    'language': tweet.lang,
                }
            }
            items.append(item)
        result = {  'items': items, 
                    'start': start, 
                    'end': end  }
                        
        return result, ''
                
    def _handle_user(self, user_id, screen_name):
        platform = SocialPlatform.objects.get(name='Twitter')
        logger.debug('Platform: {0}'.format(platform))
        
        try:
            users = SocialUser.objects.filter(handle=screen_name).filter(
                                                                user_id=user_id)
        except Exception as E:
            logger.debug('Problem filtering SocialUsers.')
            logger.debug(E)
            raise E
        
        if len(users) > 0:
            logger.debug(
                'SocialUser with that screen_name and user_id) already exists.')
            return
        else:
            try:
                user = SocialUser(
                        handle=screen_name,
                        user_id=str(user_id),
                        platform=platform,
                        profile_url='http://twitter.com/{0}'.format(screen_name)
                        )
                user.save()
            except Exception as E:
                logger.debug('Problem creating a SocialUser.')
                logger.debug('handle: {0}, user_id: {1}, platform: {2}'
                                        .format(screen_name, user_id, platform))
                logger.debug(E)
                raise E
            logger.debug('Created user {0}'.format(user))
    

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
    text_formats = ['pdf', 'xml', 'html', 'xhtml', 'txt', 'epub']
    
    def search(self, queryevent_id):
        """
        Perform a search of the Internet Archive.
        """
        
        try:
            queryevent = QueryEvent.objects.get(pk=queryevent_id)

            query = queryevent.querystring.querystring
            _params = [ p for p in queryevent.engine.parameters ]
            _start = queryevent.rangeStart
            _end = queryevent.rangeEnd

            pagesize = ( queryevent.engine.pagesize or 10 )
            
            results = []
            for i in xrange(_start, _end, pagesize):
                start = i
                end = min(start + pagesize - 1, _end)

                rows = (end - start) + 1
                start = max(start-1,0) # IA starts at 0.
                
                logger.debug('search for {0}, start: {1}, end: {2}, rows: {3}'
                                               .format(query, start, end, rows))

                params = _params + [ "q={0}".format(urllib2.quote(query)),
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

                results.append(self._handleResponse(rcontent))
        except Exception as E:
            logger.debug(E)
            return 'ERROR'
        return results
    
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
        elif mtype == 'texts':
            known = self.text_formats
            alt = []
            alttype = None
        else:
            raise MediaTypeException(
                    'Unrecognized content or mtype not provided.'    )

        # TODO: This may be overly simplistic. What if an item has multiple
        #  content types (e.g. audio and video content)? 
        files = []
        thumbs = []
        mtype_match = False    # Is at least one file the expected type?
        alttype_match = False  # Is at least one file an alternate type?
        
        for child in root:
            filename = child.attrib['name']
            ext = filename.split('.')[-1].lower()
            
            # Checks for media type mismatch.
            if ext in known:
                mtype_match = True
            elif ext in alt:
                alttype_match = True
            
            # If a file is not an XML or torrent file, consider it content.
            #  TODO: Is this too liberal?
            if ext not in ['xml', 'torrent']:
                files.append( ''.join([ baseurl, filename ]) )
            
            # Some media have thumbnails associated with them.
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
                date_published = localize_date(child.text, '%Y-%m-%d %H:%M:%S')
#                date_published = datetime.strptime(
#                                    child.text, '%Y-%m-%d %H:%M:%S' )
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
            logger.debug('item has mediatype {0}'.format(item['mediatype']))
            if item['mediatype'] == 'movies':
                mtype = 'video'
                alttype = 'audio'
            #   Audio files...
            elif item['mediatype'] == 'audio': 
                mtype = 'audio'
                alttype = 'video'
            elif item['mediatype'] == 'texts':
                mtype = 'texts'
                alttype = None

            try:    # Catch cases where declared mtype is incorrect.
                md = self._getDetails(item['identifier'], mtype)
                logger.debug('_getDetails successful')
            except MediaTypeException:
                logger.debug(
                   'Caught MediaTypeException for type {0}, trying alttype {1}.'
                    .format(mtype, alttype) )
                    
                md = self._getDetails(item['identifier'], alttype)
                mtype = alttype
            contextURL, date_pub, creator, desc, files, thumbs = md

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

    def search(self, queryevent_id): #params, query, start=1, end=10):
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
        
        try:
            queryevent = QueryEvent.objects.get(pk=queryevent_id)
            
            query = queryevent.querystring.querystring
            _params = [ p for p in queryevent.engine.parameters ]
            _start = queryevent.rangeStart
            _end = queryevent.rangeEnd
            
            logger.debug('params: {0}'.format(_params))
            
            pagesize = ( queryevent.engine.pagesize or 10 )
            
            results = []
            for i in xrange(_start, _end, pagesize):
                start = i
                end = min(start + pagesize - 1, _end)
                
                params = _params + [ "q={0}".format(urllib2.quote(query)),
                                     "start={0}".format(start),
                                     "num={0}".format((end - start) + 1),
                                     "searchType=image"  ]

                request = self.endpoint + "&".join(params)
                logger.debug('request: {0}'.format(request))
                
                response = urllib2.urlopen(request)
                results.append(self._handleResponse(response.read()))
        except Exception as E:
            logger.debug(E)
            return 'ERROR'
        return results

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
        
