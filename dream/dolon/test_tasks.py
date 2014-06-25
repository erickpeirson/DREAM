from django.test import TestCase

apikey = "AIzaSyDhlbNOLTRRVebYs5PNx9snu6SZOsQFYnM"
cx = "002775406652749371248:l-zbbsqhcte"

#["key=AIzaSyDhlbNOLTRRVebYs5PNx9snu6SZOsQFYnM",
#"cx=002775406652749371248:l-zbbsqhcte"]

from tasks import *
from managers import GoogleImageSearchManager, spawnSearch
from models import QueryString, QueryEvent, QueryItem, Engine, Thumbnail, Image
from django.core.files.base import File

import celery
from celery.result import AsyncResult, TaskSetResult
import time

thumburl = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRLchzhwk-ADaYkhcsRrdmKFYFo-g_cvqbFZMPaxNX6BeLAkuKb1x8RClk'

class TestSearch(TestCase):
    def setUp(self):
        item = QueryItem(   url='',
                            title='',
                            size=1,
                            height=1,
                            width=1,
                            mime='',
                            contextURL='',
                            thumbnailURL='')
        item.save()

        manager = GoogleImageSearchManager()
        parameters =  [    "key={0}".format(apikey),
                                "cx={0}".format(cx) ]

        engine = Engine(    parameters=parameters,
                            manager='GoogleImageSearchManager'  )
        engine.save()

        querystring = QueryString(querystring='dream act')
        querystring.save()
        queryevent = QueryEvent(    querystring=querystring,
                                    rangeStart=1,
                                    rangeEnd=10,
                                    engine=engine )
                                    
        queryevent.save()    
        
        self.item = item
        self.manager = manager
        self.engine = engine
        self.querystring = querystring
        self.queryevent = queryevent
        self.parameters = parameters
#        
    def test_spawnSearch(self):
        id, subtasks = spawnSearch(self.queryevent, testing=True)
        
#        self.assertIsInstance(id, str)
#        self.assertGreater(len(id), 0)
        
        result = TaskSetResult(id, [ AsyncResult(s) for s in subtasks ] )
        time.sleep(20)
        print result.completed_count()
#        
#    def test_spawnThumbnails(self):
#        result, response = search('dream act', 50, 59, self.manager, self.parameters)
#        queryResult, queryItems = processSearch((result, response), self.queryevent.id)    
#        
#        task = spawnThumbnails((queryResult, queryItems), self.queryevent.id)
#        
#    def test_spawn_getFile(self):
#        from celery import group, chain
#        from celery.result import AsyncResult
#        
#        job = getFile.s(thumburl)
#        r = job.apply_async()
#        result=AsyncResult(r)
#        
#        import time
#        time.sleep(5)
#        print r.state
#            
#
#    def test_getFile(self):
#        url, filename, file, mime, size = getFile(thumburl)   
#        
#        self.assertIsInstance(filename, str)
#        self.assertIsInstance(file, File)
#        self.assertIsInstance(mime, str)
#        self.assertIsInstance(size, int)
#        
#    def test_storeThumbnail(self):
#        url, filename, file, mime, size = getFile(thumburl)
#        thumbnail = storeThumbnail((url, filename, file, mime, size), self.item)
#        
#        self.assertIsInstance(thumbnail, Thumbnail)
#        self.assertEqual(thumbnail.url, thumburl)
#        self.assertEqual(thumbnail.mime, mime)
#        self.assertEqual(thumbnail.size, size)    
#    
#    def test_search(self):
#    
#        result, response = search('dream act', 1, 10, self.engine.manager, self.parameters)
#        
#        self.assertIsInstance(result, dict)
#        self.assertIsInstance(response, dict)
#        self.assertEqual(len(result['items']), 10)
#        
#    def test_processSearch(self):
#        result, response = search('dream act', 1, 10, self.manager, self.parameters)
#        queryResult, queryItems = processSearch((result, response), self.queryevent.id)
#        
#        self.assertIsInstance(queryResult, QueryResult)
#        self.assertIsInstance(queryItems, list)
#        self.assertIsInstance(queryItems[0], QueryItem)
        

        
        