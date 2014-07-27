from django.test import TestCase

from ..tasks import *
from ..models import *
from django.contrib.auth.models import User
from django.core.files import File

import celery
from celery.result import AsyncResult, TaskSetResult
import time
import cPickle as pickle

thumburl = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRLchzhwk-ADaYkhcsRrdmKFYFo-g_cvqbFZMPaxNX6BeLAkuKb1x8RClk'
contexturl = 'http://www.wallstreetdaily.com/2014/07/21/immigration-and-obama-dream-act/'

responsePickle = './dolon/tests/testdata/searchresponse.pickle'
resultPickle = './dolon/tests/testdata/searchresult.pickle'

with open(responsePickle, 'r') as f:
    searchResponse = pickle.load(f)
with open(resultPickle, 'r') as f:
    searchResult = pickle.load(f)
        
class TestSearch(TestCase):
    def setUp(self):
        self.user = User()
        self.user.save()

        self.querystring = QueryString(querystring='dream act legislation')
        self.querystring.save()

        self.engine = Engine(
            parameters = [  "key=AIzaSyDhlbNOLTRRVebYs5PNx9snu6SZOsQFYnM",
                            "cx=002775406652749371248:l-zbbsqhcte"  ],
            manager='GoogleImageSearchManager',
            daylimit=100,
            monthlimit=3000 )
        self.engine.save()

        self.queryevent = QueryEvent(
            querystring=self.querystring,
            rangeStart=1,
            rangeEnd=10,
            engine=self.engine,
            creator=self.user    )
        self.queryevent.save()    

    def test_search(self):
        """
        search should return a tuple containing two dicts.
        """
        
        manager_name = 'GoogleImageSearchManager'
        qstring = 'dream act'
        start=1
        end=10
        params=[    "key=AIzaSyDhlbNOLTRRVebYs5PNx9snu6SZOsQFYnM",
                    "cx=002775406652749371248:l-zbbsqhcte"  ]
        
        result, response = search(qstring, start, end, manager_name, params)
        
        self.assertIsInstance(result, dict)
        self.assertIsInstance(response, dict)
        
#        with open(responsePickle, 'w') as f:
#            pickle.dump(response, f)
#        with open(resultPickle, 'w') as f:
#            pickle.dump(result, f)

    def test_processSearch(self):
        """
        processSearch should return a QueryEvent id and a list of Item ids.
        """
        qr_id, q_I = processSearch((searchResult,searchResponse), self.queryevent.id)
        self.assertIsInstance(qr_id, int, 'Expecting int (QueryResult id)')
        self.assertIsInstance(q_I, list, 'Expecting list (Items)')
        self.assertIsInstance(q_I[0], int, 'Expecting int (Item id)')
        
        test_qresult = QueryResult.objects.get(pk=qr_id)
        self.assertIsInstance(test_qresult, QueryResult, 'Expected a QueryResult')
        
        test_item = Item.objects.get(pk=q_I[0])
        self.assertIsInstance(test_item, Item, 'Expected an Item')
        self.assertTrue(hasattr(test_item, 'imageitem'))
        
        qr_items = test_qresult.resultitems.all()
        for i in qr_items:
            self.assertEqual(i.type, 'image')
            self.assertTrue(hasattr(i.item, 'imageitem'))
            

    def test_getFile(self):
        """
        getFile should return a url, filename, filepath, mime-type, and size.
        """

        url, filename, fpath, mime, size = getFile(thumburl)
        # url
        self.assertEqual(url, thumburl)
        
        # filename
        self.assertIsInstance(filename, str)
        self.assertGreater(len(filename), 0)
        
        # fpath
        self.assertIsInstance(fpath, str)
        self.assertGreater(len(fpath), 0)
        
        # mime
        self.assertIsInstance(mime, str)
        self.assertGreater(len(mime), 0)

        # size
        self.assertIsInstance(size, int)
        self.assertGreater(size, 0)
        
    def test_storeImage(self):
        """
        storeImage takes the result of getFile and an Image id, and should
        return an Image id.
        """
        
        result = getFile(thumburl)
        image = Image(url=thumburl)
        image.save()
        id = storeImage(result, image.id)
        
        self.assertIsInstance(id, int)
        
        test_image = Image.objects.get(pk=id)
        self.assertIsInstance(test_image, Image)
        
        self.assertEqual(test_image.size, result[4])
        self.assertEqual(test_image.mime, result[3])
        self.assertEqual(test_image.url, result[0])
        self.assertIsInstance(test_image.image, File)

    def test_storeThumbnail(self):
        """
        storeThumbnail takes the result of getFile and a Thumbnail id, and 
        should return a Thumbnail id.
        """
        
        result = getFile(thumburl)
        image = Thumbnail(url=thumburl)
        image.save()
        id = storeThumbnail(result, image.id)
        
        self.assertIsInstance(id, int)
        
        test_image = Thumbnail.objects.get(pk=id)
        self.assertIsInstance(test_image, Thumbnail)
        
        self.assertEqual(test_image.mime, result[3])
        self.assertEqual(test_image.url, result[0])
        self.assertIsInstance(test_image.image, File)        

    def test_getStoreContext(self):
        """
        getStoreContext takes a url and a Context id, and returns the Context
        id after updating it with HTML content.
        """
        
        context = Context(url=contexturl)
        context.save()
        
        c_id = getStoreContext(contexturl, context.id)
        
        self.assertIsInstance(c_id, int)
        
        test_context = Context.objects.get(pk=c_id)
        self.assertIsInstance(test_context, Context)
        self.assertEqual(test_context.url, contexturl)
        self.assertGreater(len(test_context.content), 0)
        
    def test_QueryResultItem_save(self):    
        base_params = {
            'title': 'testTitle',
            'size': 5,
            'contextURL': 'http://somewhere/over/here',
            'url': 'http://right/here',
            'creator': '',
            'thumbnailURL': ['']
            }

        image_params = {k:v for k,v in base_params.iteritems() }
        image_params.update({
            'type': 'image',                        
            'height': 5,
            'width': 5,
            'mime': 'image/jpeg',
            'thumbnailURL': 'http://somewhere/else'
            })
            
        video_params = {k:v for k,v in base_params.iteritems() }
        video_params.update({
            'type': 'video',
            'length': 500,
            'mime': 'video/mpeg'
            })
            
        audio_params = {k:v for k,v in base_params.iteritems() }
        audio_params.update({
            'type': 'audio',
            'length': 500,
            'mime': 'audio/audio'
            })
        
        # Test for image
        qri = QueryResultItem(
                url = image_params['url'],
                contextURL = image_params['contextURL'],
                type = image_params['type'],
                params = pickle.dumps(image_params)
                )
        qri.save()
            
        self.assertIsInstance(qri, QueryResultItem)
        self.assertIsInstance(qri.item, Item)
        self.assertTrue(hasattr(qri.item, 'imageitem'))
        
        # Test for video
        qrv = QueryResultItem(
                url = video_params['url']+'/asdf',
                contextURL = video_params['contextURL'],
                type = video_params['type'],
                params = pickle.dumps(video_params)
                )
        qrv.save()        
        
        self.assertIsInstance(qrv, QueryResultItem)
        self.assertIsInstance(qrv.item, Item)
        self.assertTrue(hasattr(qrv.item, 'videoitem'))       
        
        # Test for audio
        qra = QueryResultItem(
                url = audio_params['url']+'/asdff',
                contextURL = audio_params['contextURL'],
                type = audio_params['type'],
                params = pickle.dumps(audio_params)
                )
        qra.save()        
        
        self.assertIsInstance(qra, QueryResultItem)
        self.assertIsInstance(qra.item, Item)
        self.assertTrue(hasattr(qra.item, 'audioitem'))           
        
class TestResetSearchUsage(TestCase):
    def setUp(self):
        self.user = User()
        self.user.save()

        self.querystring = QueryString(querystring='dream act legislation')
        self.querystring.save()

        self.engine = Engine(
            parameters = [  "key=AIzaSyDhlbNOLTRRVebYs5PNx9snu6SZOsQFYnM",
                            "cx=002775406652749371248:l-zbbsqhcte"  ],
            manager='GoogleImageSearchManager',
            daylimit=100,
            monthlimit=3000 )
        self.engine.save()

        self.queryevent = QueryEvent(
            querystring=self.querystring,
            rangeStart=1,
            rangeEnd=10,
            engine=self.engine,
            creator=self.user    )
        self.queryevent.save()   

        
    def test_reset_dayusage(self):
        self.engine.dayusage += 5
        
        test_engine = Engine.objects.get(pk=self.engine.id)
        reset_dayusage()
        self.assertEqual(test_engine.dayusage, 0)
        
    def test_reset_monthusage(self):
        self.engine.monthusage += 5
        
        test_engine = Engine.objects.get(pk=self.engine.id)        
        reset_monthusage()
        self.assertEqual(test_engine.monthusage, 0)  
        
    def test_try_dispatch(self):
        self.engine.monthusage = 0
        self.engine.dayusage = 0
        self.engine.save()
            
        try_dispatch(self.queryevent)
        
        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
        test_engine = Engine.objects.get(pk=self.engine.id)
        self.assertTrue(test_queryevent.dispatched)
        self.assertEqual(test_engine.dayusage, 1)
        self.assertEqual(test_engine.monthusage, 1)
        
    def test_try_dispatch_overday(self):
        self.engine.monthusage = 0
        self.engine.dayusage = 100
        self.engine.save()
        
        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
        self.assertFalse(test_queryevent.dispatched) 
        
    def test_try_dispatch_overmonth(self):
        self.engine.dayusage = 0
        self.engine.monthusage = 100
        self.engine.save()
        
        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
        self.assertFalse(test_queryevent.dispatched)        
        
    def test_trigger_dispatchers(self):
        trigger_dispatchers()
        
        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
        test_engine = Engine.objects.get(pk=self.engine.id)
        self.assertTrue(test_queryevent.dispatched)
        self.assertEqual(test_engine.dayusage, 1)
        self.assertEqual(test_engine.monthusage, 1)        
        
        