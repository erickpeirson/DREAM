from django.test import TestCase

from ..tasks import *
from .. import tasks
from ..models import *
from django.contrib.auth.models import User
from django.core.files import File

import celery
from celery.result import AsyncResult, TaskSetResult
import time
import cPickle as pickle

thumburl = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRLchzhwk-ADaYkhcsRrdmKFYFo-g_cvqbFZMPaxNX6BeLAkuKb1x8RClk'
contexturl = 'http://www.wallstreetdaily.com/2014/07/21/immigration-and-obama-dream-act/'
mp4url = 'http://ia600801.us.archive.org/34/items/YourDreamStopsHereDreamActPart1/FOUND_GREEN_FB_DREAMACT_SD_FINAL_v1b-WEB_512kb.mp4'
mp4path = './dolon/tests/testdata/tmps6qfCZ.mp4'
mp3url = 'http://ia600404.us.archive.org/32/items/TheDreamAct_390/TheDreamAct2_vbr.mp3'
mp3path = './dolon/tests/testdata/test.mp3'

responsePickle = './dolon/tests/testdata/searchresponse.pickle'
responsePickle_ia = './dolon/tests/testdata/searchresponse_ia.pickle'
resultPickle = './dolon/tests/testdata/searchresult.pickle'
resultPickle_ia = './dolon/tests/testdata/searchresult_ia.pickle'

# Test data, so that we don't make so many remote requests.
with open(responsePickle, 'r') as f:
    searchResponse = pickle.load(f)
with open(resultPickle, 'r') as f:
    searchResult = pickle.load(f)
    
with open(responsePickle_ia, 'r') as f:
    searchResponse_ia = pickle.load(f)
with open(resultPickle_ia, 'r') as f:
    searchResult_ia = pickle.load(f)    

class TestCreateItem(TestCase):
    def setUp(self):
        self.user = User()
        self.user.save()    
        
        self.querystring = QueryString(querystring='dream act legislation')
        self.querystring.save()        

        self.ia_engine = Engine(
            parameters = [],
            manager = 'InternetArchiveManager',
            daylimit=1000,
            monthlimit=30000 )
        self.ia_engine.save()     
        
        self.queryevent = QueryEvent(
            querystring=self.querystring,
            rangeStart=1,
            rangeEnd=10,
            engine=self.ia_engine,
            creator=self.user    )
        self.queryevent.save()         
        
        qid, self.queryitems = processSearch(   
                    (searchResult_ia, searchResponse_ia), self.queryevent.id  )
                    
        qid_, self.queryitems_ = processSearch(
                    (searchResult, searchResponse), self.queryevent.id  )
#
#    def test_get_params(self):
#        resultitem = QueryResultItem.objects.get(pk=self.queryitems[0])
#        params, length, size, creator, date = tasks._get_params(resultitem)
#        self.assertEqual(str(date), '2011-12-09 15:44:06-07:00')
#        self.assertEqual(creator, 'wuagnews@gmail.com')
#        
#    def test_get_default_audioitem(self):
#        resultitem = QueryResultItem.objects.get(pk=self.queryitems[0])    
#        i = tasks._get_default(AudioItem, resultitem)
#        
#        self.assertIsInstance(i, Item)
#        self.assertTrue(hasattr(i, 'audioitem'))
#        
#    def test_get_default_wrongtype(self):
#        """
#        If _get_default's itemtype is inappropriate for the Item with the
#        current URL, a ValueError should be raised.
#        """
#        
#        resultitem = QueryResultItem.objects.get(pk=self.queryitems[0])    
#        self.assertRaises(ValueError, tasks._get_default, ImageItem, resultitem)
#    
    def test_create_audio_item(self):
        for qi in self.queryitems:
            resultitem = QueryResultItem.objects.get(pk=qi)
            if resultitem.type == 'audio':
                i = tasks._create_audio_item(resultitem)
                self.assertGreater(len(i.audio_segments.all()), 0)
                self.assertNotEqual(i.creationDate, None)
#        
#    def test_create_video_item(self):
#        resultitem = QueryResultItem.objects.get(pk=self.queryitems[5])    
#        i = tasks._create_video_item(resultitem)
#        
#        self.assertGreater(len(i.videos.all()), 0)
#        self.assertNotEqual(i.creationDate, None)
#        
#    def test_create_image_item(self):
#        resultitem = QueryResultItem.objects.get(pk=self.queryitems_[0])    
#        i = tasks._create_image_item(resultitem)        
#        self.assertGreater(len(i.images.all()), 0)
                        
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
        
        self.ia_engine = Engine(
            parameters = [],
            manager = 'InternetArchiveManager',
            daylimit=1000,
            monthlimit=30000 )
        self.ia_engine.save()

        self.queryevent = QueryEvent(
            querystring=self.querystring,
            rangeStart=1,
            rangeEnd=10,
            engine=self.engine,
            creator=self.user    )
        self.queryevent.save()    

#    def test_search_ia(self):
#        """
#        search should return a tuple containing two dicts.
#        """
#        
#        manager_name = 'InternetArchiveManager'
#        qstring = 'dream act'
#        start=1
#        end=10
#        
#        result, response = search(qstring, start, end, manager_name, [])
#        
##        with open(responsePickle_ia, 'w') as f:
##            pickle.dump(response, f)
##        with open(resultPickle_ia, 'w') as f:
##            pickle.dump(result, f)        
#        
#        self.assertIsInstance(result, dict)
#        self.assertIsInstance(response, dict)
#        
#    def test_processSearch_ia(self):
#        """
#        processSearch should return a QueryEvent id and a list of Item ids.
#        """
#        qr_id, q_I = processSearch( (searchResult_ia,searchResponse_ia), 
#                                    self.queryevent.id  )
#        self.assertIsInstance(qr_id, int, 'Expecting int (QueryResult id)')
#        self.assertIsInstance(q_I, list, 'Expecting list (Items)')
#        self.assertIsInstance(q_I[0], int, 'Expecting int (Item id)')
#        
#        test_qresult = QueryResult.objects.get(pk=qr_id)
#        self.assertIsInstance(  test_qresult, QueryResult, 
#                                'Expected a QueryResult'    )
#        
#        test_item = Item.objects.get(pk=q_I[0])
#        self.assertIsInstance(test_item, Item, 'Expected an Item')
#        
#        qr_items = test_qresult.resultitems.all()
#        for i in qr_items:
#            self.assertTrue(i.type in ['audio', 'video'])
#            
#    def test_getFile_mp4(self):
#        """
#        getFile should return a url, filename, filepath, mime-type, and size.
#        """
#
#        url, filename, fpath, mime, size = getFile(mp4url)
#        # url
#        self.assertEqual(url, mp4url)
#        
#        # filename
#        self.assertIsInstance(filename, str)
#        self.assertGreater(len(filename), 0)
#        
#        # fpath
#        self.assertIsInstance(fpath, str)
#        self.assertGreater(len(fpath), 0)
#        
#        # mime
#        self.assertIsInstance(mime, str)
#        self.assertGreater(len(mime), 0)
#
#        # size
#        self.assertIsInstance(size, int)
#        self.assertGreater(size, 0)
#            
#
#    def test_search_google(self):
#        """
#        search should return a tuple containing two dicts.
#        """
#        
#        manager_name = 'GoogleImageSearchManager'
#        qstring = 'dream act'
#        start=1
#        end=10
#        params=[    "key=AIzaSyDhlbNOLTRRVebYs5PNx9snu6SZOsQFYnM",
#                    "cx=002775406652749371248:l-zbbsqhcte"  ]
#        
#        result, response = search(qstring, start, end, manager_name, params)
#        
#        self.assertIsInstance(result, dict)
#        self.assertIsInstance(response, dict)
#
##        with open(responsePickle, 'w') as f:
##            pickle.dump(response, f)
##        with open(resultPickle, 'w') as f:
##            pickle.dump(result, f)
#
#    def test_processSearch_google(self):
#        """
#        processSearch should return a QueryEvent id and a list of Item ids.
#        """
#        qr_id, q_I = processSearch((searchResult,searchResponse), self.queryevent.id)
#        self.assertIsInstance(qr_id, int, 'Expecting int (QueryResult id)')
#        self.assertIsInstance(q_I, list, 'Expecting list (Items)')
#        self.assertIsInstance(q_I[0], int, 'Expecting int (Item id)')
#        
#        test_qresult = QueryResult.objects.get(pk=qr_id)
#        self.assertIsInstance(test_qresult, QueryResult, 'Expected a QueryResult')
#        
#        test_item = Item.objects.get(pk=q_I[0])
#        self.assertIsInstance(test_item, Item, 'Expected an Item')
#        self.assertTrue(hasattr(test_item, 'imageitem'))
#        
#        qr_items = test_qresult.resultitems.all()
#        for i in qr_items:
#            self.assertEqual(i.type, 'image')
#            self.assertTrue(hasattr(i.item, 'imageitem'))
#            
#
#    def test_getFile(self):
#        """
#        getFile should return a url, filename, filepath, mime-type, and size.
#        """
#
#        url, filename, fpath, mime, size = getFile(thumburl)
#        # url
#        self.assertEqual(url, thumburl)
#        
#        # filename
#        self.assertIsInstance(filename, str)
#        self.assertGreater(len(filename), 0)
#        
#        # fpath
#        self.assertIsInstance(fpath, str)
#        self.assertGreater(len(fpath), 0)
#        
#        # mime
#        self.assertIsInstance(mime, str)
#        self.assertGreater(len(mime), 0)
#
#        # size
#        self.assertIsInstance(size, int)
#        self.assertGreater(size, 0)
#        
#    def test_storeImage(self):
#        """
#        storeImage takes the result of getFile and an Image id, and should
#        return an Image id.
#        """
#        
#        result = getFile(thumburl)
#        image = Image(url=thumburl)
#        image.save()
#        id = storeImage(result, image.id)
#        
#        self.assertIsInstance(id, int)
#        
#        test_image = Image.objects.get(pk=id)
#        self.assertIsInstance(test_image, Image)
#        
#        self.assertEqual(test_image.size, result[4])
#        self.assertEqual(test_image.mime, result[3])
#        self.assertEqual(test_image.url, result[0])
#        self.assertIsInstance(test_image.image, File)
#        
#    def test_spawnRetrieveImages(self):        
#        result = getFile(thumburl)
#        image = Image(url=thumburl)
#        image.save()
#        
#        queryset = [image,]
#        
#        result_id, results = spawnRetrieveImages(queryset)
#
#        self.assertIsInstance(result_id, str)
#        self.assertIsInstance(results, list)
#
#
#    def test_spawnRetrieveAudio(self):        
#        url = mp3url
#        filename = 'test.mp3'
#        fpath = mp3path
#        mime = 'audio/mpeg'
#        size = 5216624 
#        result = ( url, filename, fpath, mime, size)
#        audio = Audio(url=url)
#        audio.save()
#        
#        queryset = [audio,]
#        
#        result_id, results = spawnRetrieveAudio(queryset)
#        
#        self.assertIsInstance(result_id, str)
#        self.assertIsInstance(results, list)
#        
#    def test_spawnRetrieveVideo(self):        
#        result = ('http://ia600801.us.archive.org/34/items/YourDreamStopsHereDreamActPart1/FOUND_GREEN_FB_DREAMACT_SD_FINAL_v1b-WEB_512kb.mp4', 'FOUND_GREEN_FB_DREAMACT_SD_FINAL_v1b-WEB_512kb.mp4', mp4path, 'video/mp4', 3958303)
#
#        video = Video(url=mp4url)
#        video.save()
#        
#        queryset = [video,]
#        
#        result_id, results = spawnRetrieveVideo(queryset)
#        
#        self.assertIsInstance(result_id, str)
#        self.assertIsInstance(results, list)        
#
#    def test_storeAudio(self):
#        """
#        storeImage takes the result of getFile and an Image id, and should
#        return an Image id.
#        """
#        
#        url = mp3url
#        filename = 'test.mp3'
#        fpath = mp3path
#        mime = 'audio/mpeg'
#        size = 5216624 
#        result = ( url, filename, fpath, mime, size)
#
#        audio = Audio(url=url)
#        audio.save()
#        id = storeAudio(result, audio.id)
#        
#        self.assertIsInstance(id, int)
#        
#        test_audio = Audio.objects.get(pk=id)
#        self.assertIsInstance(test_audio, Audio)
#        
#        self.assertEqual(test_audio.size, result[4])
#        self.assertEqual(test_audio.mime, result[3])
#        self.assertEqual(test_audio.url, result[0])
#        self.assertIsInstance(test_audio.audio_file, File)
#
#    def test_storeVideo(self):
#        """
#        storeImage takes the result of getFile and an Image id, and should
#        return an Image id.
#        """
#
#        result = ('http://ia600801.us.archive.org/34/items/YourDreamStopsHereDreamActPart1/FOUND_GREEN_FB_DREAMACT_SD_FINAL_v1b-WEB_512kb.mp4', 'FOUND_GREEN_FB_DREAMACT_SD_FINAL_v1b-WEB_512kb.mp4', mp4path, 'video/mp4', 3958303)
#
#        video = Video(url=mp4url)
#        video.save()
#        id = storeVideo(result, video.id)
#        
#        self.assertIsInstance(id, int)
#        
#        test_video = Video.objects.get(pk=id)
#        self.assertIsInstance(test_video, Video)
#        
#        self.assertEqual(test_video.size, result[4])
#        self.assertEqual(test_video.mime, result[3])
#        self.assertEqual(test_video.url, result[0])
#        self.assertIsInstance(test_video.video, File)
#        
#
#    def test_storeThumbnail(self):
#        """
#        storeThumbnail takes the result of getFile and a Thumbnail id, and 
#        should return a Thumbnail id.
#        """
#        
#        result = getFile(thumburl)
#        image = Thumbnail(url=thumburl)
#        image.save()
#        id = storeThumbnail(result, image.id)
#        
#        self.assertIsInstance(id, int)
#        
#        test_image = Thumbnail.objects.get(pk=id)
#        self.assertIsInstance(test_image, Thumbnail)
#        
#        self.assertEqual(test_image.mime, result[3])
#        self.assertEqual(test_image.url, result[0])
#        self.assertIsInstance(test_image.image, File)        
#
#    def test_getStoreContext(self):
#        """
#        getStoreContext takes a url and a Context id, and returns the Context
#        id after updating it with HTML content.
#        """
#        
#        context = Context(url=contexturl)
#        context.save()
#        
#        contexturl2 = 'https://archive.org/details/DreamActAudio'
#        context2 = Context(url=contexturl2)
#        context2.save()
#        
#        c_id = getStoreContext(contexturl, context.id)
#        c_id2 = getStoreContext(contexturl2, context2.id)        
#        
#        self.assertIsInstance(c_id, int)
#        self.assertIsInstance(c_id2, int)        
#        
#        test_context = Context.objects.get(pk=c_id)
#        test_context2 = Context.objects.get(pk=c_id2)        
#        self.assertIsInstance(test_context, Context)
#        self.assertEqual(test_context.url, contexturl)
#        self.assertGreater(len(test_context.content), 0)
#        self.assertIsInstance(test_context2, Context)
#        self.assertEqual(test_context2.url, contexturl2)
#        self.assertGreater(len(test_context2.content), 0)        
        
    def test_QueryResultItem_save(self):    
        """
        Changes 2014-08-26: :class:`.Item`\s are no longer created automatically
        when a :class:`.QueryResultItem` is saved. So we're now just testing
        that the :class:`.QueryResultItem` is getting saved.
        """
        
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
        
        # Test for video
        qrv = QueryResultItem(
                url = video_params['url']+'/asdf',
                contextURL = video_params['contextURL'],
                type = video_params['type'],
                params = pickle.dumps(video_params)
                )
        qrv.save()        
        
        self.assertIsInstance(qrv, QueryResultItem)     
        
        # Test for audio
        qra = QueryResultItem(
                url = audio_params['url']+'/asdff',
                contextURL = audio_params['contextURL'],
                type = audio_params['type'],
                params = pickle.dumps(audio_params)
                )
        qra.save()        
        
        self.assertIsInstance(qra, QueryResultItem)
        
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
            rangeEnd=2,
            engine=self.engine,
            creator=self.user    )
        self.queryevent.save()   
#
#        
#    def test_reset_dayusage(self):
#        self.engine.dayusage += 5
#        
#        test_engine = Engine.objects.get(pk=self.engine.id)
#        reset_dayusage()
#        self.assertEqual(test_engine.dayusage, 0)
#        
#    def test_reset_monthusage(self):
#        self.engine.monthusage += 5
#        
#        test_engine = Engine.objects.get(pk=self.engine.id)        
#        reset_monthusage()
#        self.assertEqual(test_engine.monthusage, 0)  
#
#
#    def test_try_dispatch_nodaylimit(self):
#        self.engine.daylimit = None
#        self.engine.save()
#        
#        try_dispatch(self.queryevent)
#        
#        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
#        test_engine = Engine.objects.get(pk=self.engine.id)
#        self.assertTrue(test_queryevent.dispatched)
#        self.assertEqual(test_engine.dayusage, 1)
#        self.assertEqual(test_engine.monthusage, 1)        
#        
#    def test_try_dispatch_nomonthlimit(self):
#        self.engine.monthlimit = None
#        self.engine.save()
#        
#        try_dispatch(self.queryevent)
#        
#        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
#        test_engine = Engine.objects.get(pk=self.engine.id)
#        self.assertTrue(test_queryevent.dispatched)
#        self.assertEqual(test_engine.dayusage, 1)
#        self.assertEqual(test_engine.monthusage, 1)        
#
#    def test_try_dispatch_nopagelimit(self):
#        self.engine.pagelimit = None
#        self.engine.save()
#        
#        try_dispatch(self.queryevent)
#        
#        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
#        test_engine = Engine.objects.get(pk=self.engine.id)
#        self.assertTrue(test_queryevent.dispatched)
#        self.assertEqual(test_engine.dayusage, 1)
#        self.assertEqual(test_engine.monthusage, 1)    
#        
#    def test_try_dispatch_nodaylimit(self):
#        self.engine.daylimit = None
#        self.engine.save()
#        
#        try_dispatch(self.queryevent)
#        
#        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
#        test_engine = Engine.objects.get(pk=self.engine.id)
#        self.assertTrue(test_queryevent.dispatched)
#        self.assertEqual(test_engine.dayusage, 1)
#        self.assertEqual(test_engine.monthusage, 1)     
        
    def test_try_dispatch_nonsense(self):
        self.queryevent.rangeStart = 5
        
        try_dispatch(self.queryevent)
        
        
#    def test_try_dispatch(self):
#        self.engine.monthusage = 0
#        self.engine.dayusage = 0
#        self.engine.save()
#            
#        try_dispatch(self.queryevent)
#        
#        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
#        test_engine = Engine.objects.get(pk=self.engine.id)
#        self.assertTrue(test_queryevent.dispatched)
#        self.assertEqual(test_engine.dayusage, 1)
#        self.assertEqual(test_engine.monthusage, 1)
#        
#    def test_try_dispatch_overday(self):
#        self.engine.monthusage = 0
#        self.engine.dayusage = 100
#        self.engine.save()
#        
#        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
#        self.assertFalse(test_queryevent.dispatched) 
#        
#    def test_try_dispatch_overmonth(self):
#        self.engine.dayusage = 0
#        self.engine.monthusage = 100
#        self.engine.save()
#        
#        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
#        self.assertFalse(test_queryevent.dispatched)        
#        
#    def test_trigger_dispatchers(self):
#        trigger_dispatchers()
#        
#        test_queryevent = QueryEvent.objects.get(pk=self.queryevent.id)
#        test_engine = Engine.objects.get(pk=self.engine.id)
#        self.assertTrue(test_queryevent.dispatched)
#        self.assertEqual(test_engine.dayusage, 1)
#        self.assertEqual(test_engine.monthusage, 1)        
        
        