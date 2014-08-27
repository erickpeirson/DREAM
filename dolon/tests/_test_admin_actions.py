from django.test import TestCase
from django.contrib.auth.models import User

from ..admin import *
from ..models import *
from ..admin_actions import *
from .. import admin_actions

import time

class TestQueryEventActions(TestCase):
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
            rangeEnd=2,
            engine=self.ia_engine,
            creator=self.user    )
        self.queryevent.save()           
    
    def test_reset_failed(self):
        """FAILED or ERRORed QueryEvents should have status set PENDING."""
        
        self.queryevent.state = 'FAILED'
        self.queryevent.dispatched = True
        self.queryevent.save()
        
        reset(QueryEventAdmin, None, [self.queryevent])
        
        qe_after = QueryEvent.objects.get(pk=self.queryevent.id)
        
        self.assertEqual(qe_after.state, 'PENDING')
        
    def test_reset_errored(self):
        """FAILED or ERRORed QueryEvents should have status set PENDING."""
        
        self.queryevent.state = 'ERROR'
        self.queryevent.dispatched = True
        self.queryevent.save()
        
        reset(QueryEventAdmin, None, [self.queryevent])
        
        qe_after = QueryEvent.objects.get(pk=self.queryevent.id)
        self.assertEqual(qe_after.state, 'PENDING')
        
    def test_dispatch(self):
        """
        QueryEvent.dispatched should be True, and should have an associated
        GroupTask in QueryEvent.search_task.
        """
        
        dispatch(QueryEventAdmin, None, [self.queryevent])
        
        qe_after = QueryEvent.objects.get(pk=self.queryevent.id)
        
        self.assertTrue(qe_after.dispatched)
        self.assertIsInstance(qe_after.search_task, GroupTask)        

class TestItemActions(TestCase):
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
            rangeEnd=2,
            engine=self.ia_engine,
            creator=self.user    )
        self.queryevent.save()       
    
        context = Context(url = 'thefirstcontext')
        context.save()
        tag = Tag(text = 'the first tag')
        tag.save()
        context2 = Context(url = 'thesecondcontext')
        context2.save()
        tag2 = Tag(text = 'the second tag')
        tag2.save()
        tag3 = Tag(text = 'the third and final tag')
        tag3.save()
    
        self.imageitem = ImageItem(url = 'theimageitem')
        self.imageitem.save()        
        self.imageitem.context.add(context)
        self.imageitem.events.add(self.queryevent)
        self.imageitem.tags.add(tag)
        self.imageitem.save()
        self.imageitem2 = ImageItem(url = 'theimageitem2')
        self.imageitem2.save()        
        self.imageitem2.context.add(context2)
        self.imageitem2.events.add(self.queryevent)        
        self.imageitem2.tags.add(tag2)
        self.imageitem2.tags.add(tag3)        
        self.imageitem2.save()                
        
        self.audioitem = AudioItem(url = 'theaudioitem')
        self.audioitem.save()
        self.audioitem2 = AudioItem(url = 'theotheraudioitem')
        self.audioitem2.save()        
        self.videoitem = VideoItem(url = 'thevideoitem')
        self.videoitem.save()
        self.videoitem2 = VideoItem(url = 'theothervideoitem')
        self.videoitem2.save()        
        self.textitem = TextItem(url = 'thetextitem')
        self.textitem.save()
        self.textitem2 = TextItem(url = 'theothertextitem')
        self.textitem2.save()        

    def test_approve(self):
        """
        Should set Item.status to 'AP'.
        """
        approve(ItemAdmin, None, [self.imageitem, self.audioitem])
        
        iitem = ImageItem.objects.get(pk=self.imageitem.id)
        aitem = AudioItem.objects.get(pk=self.audioitem.id)        
        
        self.assertEqual(iitem.status, 'AP')
        self.assertEqual(aitem.status, 'AP')
        
    def test_reject(self):
        """
        Should set Item.status to 'RJ'.
        """
        reject(ItemAdmin, None, [self.imageitem, self.audioitem])
        
        iitem = ImageItem.objects.get(pk=self.imageitem.id)
        aitem = AudioItem.objects.get(pk=self.audioitem.id)        
        
        self.assertEqual(iitem.status, 'RJ')
        self.assertEqual(aitem.status, 'RJ')    
    
    def test_pend(self):
        """
        Should set Item.status to 'PG'.
        """
        pend(ItemAdmin, None, [self.imageitem, self.audioitem])
        
        iitem = ImageItem.objects.get(pk=self.imageitem.id)
        aitem = AudioItem.objects.get(pk=self.audioitem.id)        
        
        self.assertEqual(iitem.status, 'PG')
        self.assertEqual(aitem.status, 'PG')  
    
    def test_generateURI(self):
        """
        Should return a tuple of (identifier, title, url).
        """
        
        identifier, title, url = admin_actions._generateURI()
        
        self.assertIsInstance(identifier, str)
        self.assertGreater(len(identifier), 0)
        
        self.assertIsInstance(title, str)
        self.assertGreater(len(title), 0)        
        
        self.assertIsInstance(url, str)
        self.assertGreater(len(url), 0)        
        
    def test_prepMerge(self):
        """
        Should generate a new :class:`.Item` based on ``itemclass``, with
        Item.type == ``type``.
        """
        
        itemclass = ImageItem
        type = 'image'
        
        newItem = admin_actions._prepMerge(itemclass, type)
        
        self.assertIsInstance(newItem, itemclass)
        self.assertEqual(newItem.type, type)
        self.assertGreater(len(newItem.url), 0)        
        self.assertGreater(len(newItem.title), 0)        
        
    def test_mergeItem(self):
        """
        Should perform merge operations common to all :class:`.Item` subclasses.
        """
        
        queryset = [ self.imageitem, self.imageitem2 ]
        itemclass = ImageItem
        type = 'image'        
        newItem = admin_actions._mergeItem(queryset,itemclass, type)
        
        self.imageitem.status = 'AP'    # One item is approved.
        
        self.assertIsInstance(newItem, itemclass)
        self.assertEqual(newItem.type, type)
        self.assertGreater(len(newItem.url), 0)        
        self.assertGreater(len(newItem.title), 0)
        
        self.assertEqual(len(newItem.tags.all()), 3)        # Three tags
        self.assertEqual(len(newItem.context.all()), 2)     # Two contexts
        self.assertEqual(len(newItem.events.all()), 1)      # One event
        
        iitem = ImageItem.objects.get(pk=self.imageitem.id)
        self.assertTrue(iitem.hide)         # Merged items should be hidden...
        self.assertFalse(newItem.hide)      # ... but not the new item.
        
    def test_mergeImage(self):
        thumb1 = Thumbnail(url = 'a thumbnail')
        thumb1.save()
        image1 = Image(url = 'an image')
        image1.save()
        thumb2 = Thumbnail(url = 'another thumbnail')
        thumb2.save()
        image2 = Image(url = 'another image')
        image2.save()
        
        self.imageitem.thumbnail = thumb1
        self.imageitem.images.add(image1)
        self.imageitem.save()
        
        self.imageitem2.thumbnail = thumb2
        self.imageitem2.images.add(image2)
        self.imageitem2.save()
    
        i = Item.objects.get(pk=self.imageitem.id)
        i2 = Item.objects.get(pk=self.imageitem2.id)
        queryset = [ i, i2 ]
        admin_actions._mergeImage(queryset)

        iitem = ImageItem.objects.get(pk=self.imageitem.id)
        iitem2 = ImageItem.objects.get(pk=self.imageitem2.id)   

        # Merged into the same item?
        self.assertEqual(iitem.merged_with, iitem2.merged_with)
        
        # Merged items should be hidden.     
        self.assertTrue(iitem.hide)
        self.assertTrue(iitem2.hide)
        
        # The new 'parent' item should inherit contexts, tags, events.
        parent = iitem.merged_with
        self.assertEqual(len(parent.tags.all()), 3)
        self.assertEqual(len(parent.context.all()), 2)
        self.assertEqual(len(parent.events.all()), 1)
        
        # Merged item should be the correct type.
        self.assertIsInstance(parent, Item)
        self.assertTrue(hasattr(parent, 'imageitem'))
        
        # Should inherit a thumbnail.
        self.assertNotEqual(parent.imageitem.thumbnail, None)
        
        # Should pool all images.
        self.assertEqual(len(parent.imageitem.images.all()), 2)
        
    def test_mergeAudio(self):
        thumb1 = Thumbnail(url = 'a thumbnail')
        thumb1.save()
        audio1 = Audio(url = 'an audio')
        audio1.save()
        thumb2 = Thumbnail(url = 'another thumbnail')
        thumb2.save()
        audio2 = Audio(url = 'another audio')
        audio2.save()
        
        self.audioitem.thumbnail = thumb1
        self.audioitem.audio_segments.add(audio1)
        self.audioitem.save()
        
        self.audioitem2.thumbnail = thumb2
        self.audioitem2.audio_segments.add(audio2)
        self.audioitem2.save()
    
        i = Item.objects.get(pk=self.audioitem.id)
        i2 = Item.objects.get(pk=self.audioitem2.id)
        queryset = [ i, i2 ]
        admin_actions._mergeAudio(queryset)

        iitem = AudioItem.objects.get(pk=self.audioitem.id)
        iitem2 = AudioItem.objects.get(pk=self.audioitem2.id)   

        # Merged into the same item?
        self.assertEqual(iitem.merged_with, iitem2.merged_with)
        
        # Merged items should be hidden.     
        self.assertTrue(iitem.hide)
        self.assertTrue(iitem2.hide)
        
        # Merged item should be the correct type.
        self.assertIsInstance(iitem.merged_with, Item)
        self.assertTrue(hasattr(iitem.merged_with, 'audioitem'))
        
        # Should inherit a thumbnail.
        self.assertNotEqual(iitem.merged_with.audioitem.thumbnail, None)
        
        # Should pool all audio segments.
        Naudio_segments = len(iitem.merged_with.audioitem.audio_segments.all())
        self.assertEqual(Naudio_segments, 2)    
    
    def test_mergeVideo(self):
        thumb1 = Thumbnail(url = 'a thumbnail')
        thumb1.save()
        video1 = Video(url = 'a video')
        video1.save()
        thumb2 = Thumbnail(url = 'another thumbnail')
        thumb2.save()
        video2 = Video(url = 'another video')
        video2.save()
        
        self.videoitem.thumbnails.add(thumb1)
        self.videoitem.videos.add(video1)
        self.videoitem.save()
        
        self.videoitem2.thumbnails.add(thumb2)
        self.videoitem2.videos.add(video2)
        self.videoitem2.save()
    
        i = Item.objects.get(pk=self.videoitem.id)
        i2 = Item.objects.get(pk=self.videoitem2.id)
        queryset = [ i, i2 ]
        admin_actions._mergeVideo(queryset)

        iitem = VideoItem.objects.get(pk=self.videoitem.id)
        iitem2 = VideoItem.objects.get(pk=self.videoitem2.id)   

        # Merged into the same item?
        self.assertEqual(iitem.merged_with, iitem2.merged_with)
        
        # Merged items should be hidden.     
        self.assertTrue(iitem.hide)
        self.assertTrue(iitem2.hide)
        
        # Merged item should be the correct type.
        self.assertIsInstance(iitem.merged_with, Item)
        self.assertTrue(hasattr(iitem.merged_with, 'videoitem'))
        
        # Should inherit all thumbnails.
        self.assertGreater(len(iitem.merged_with.videoitem.thumbnails.all()), 0)
    
        # Should pool all videos.
        Nvideos = len(iitem.merged_with.videoitem.videos.all())
        self.assertEqual(Nvideos, 2)     

    def test_mergeText(self):

        text1 = Text(url = 'a text')
        text1.save()
        text2 = Text(url = 'another text')
        text2.save()
        
        self.textitem.original_files.add(text1)
        self.textitem2.save()
        
        self.textitem2.original_files.add(text2)
        self.textitem2.save()
    
        i = Item.objects.get(pk=self.textitem.id)
        i2 = Item.objects.get(pk=self.textitem2.id)
        queryset = [ i, i2 ]
        admin_actions._mergeText(queryset)

        iitem = TextItem.objects.get(pk=self.textitem.id)
        iitem2 = TextItem.objects.get(pk=self.textitem2.id)   

        # Merged into the same item?
        self.assertEqual(iitem.merged_with, iitem2.merged_with)
        
        # Merged items should be hidden.     
        self.assertTrue(iitem.hide)
        self.assertTrue(iitem2.hide)
        
        # Merged item should be the correct type.
        self.assertIsInstance(iitem.merged_with, Item)
        self.assertTrue(hasattr(iitem.merged_with, 'textitem'))
    
        # Should pool all texts.
        Ntexts = len(iitem.merged_with.textitem.original_files.all())
        self.assertEqual(Ntexts, 2)         

    def test_merge_mismatched(self):
        """
        Since we've already tested merge functionality above, focus here on
        exceptions.
        """
        
        # Can't merge Items of different types!
        i = Item.objects.get(pk=self.textitem.id)
        i2 = Item.objects.get(pk=self.videoitem.id)
        queryset = [ i, i2 ]
        result = merge(ItemAdmin, None, queryset)

        self.assertEqual(result, None)
        
        iitem = TextItem.objects.get(pk=self.textitem.id)
        iitem2 = VideoItem.objects.get(pk=self.videoitem.id)   
        
        # Merge failed, not hidden.
        self.assertEqual(iitem.merged_with, None)
        self.assertFalse(iitem.hide)
        self.assertEqual(iitem2.merged_with, None)
        self.assertFalse(iitem2.hide)
    
    def test_merge_ok(self):

        i = Item.objects.get(pk=self.textitem.id)
        i2 = Item.objects.get(pk=self.textitem2.id)
        queryset = [ i, i2 ]
        merge(ItemAdmin, None, queryset)
        
        iitem = TextItem.objects.get(pk=self.textitem.id)
        iitem2 = TextItem.objects.get(pk=self.textitem2.id)   
        
        # Merge succeeded; hidden.
        self.assertNotEqual(iitem.merged_with, None)
        self.assertTrue(iitem.hide)
        self.assertNotEqual(iitem2.merged_with, None)
        self.assertTrue(iitem2.hide)        
        self.assertEqual(iitem.merged_with, iitem2.merged_with)
    
class TestImageActions(TestCase):
    def setUp(self):
        self.image = Image(url='http://diging.github.io/tethne/doc/0.6.1-beta/_static/logo_round.png')
        self.image.save()
        
    def test_retrieve_image(self):
        self.assertEqual(self.image.image, None)
        retrieve_image(ImageAdmin, None, [self.image])
        time.sleep(5)   # Wait for the image to download.
        
        image = Image.objects.get(pk=self.image.id)
        self.assertNotEqual(image.image, None)
        
class TestContextActions(TestCase):
    def setUp(self):
        self.context = Context(url='http://diging.github.io/tethne/')
        self.context.save()
        
        params = DiffBotManager().prep_request(
                    'article', 
                    'http://diging.github.io/tethne/',
                    []  )
        self.diffbot_request = DiffBotRequest(
                                type='article',
                                parameters=params   )
        self.diffbot_request.save()

    def test_retrieve_context(self):
        """
        Retrieves context, and creates a diffbot request, for each context.
        """
        retrieve_context(ContextAdmin, None, [self.context])
        time.sleep(10)
        
        context = Context.objects.get(pk=self.context.id)
        self.assertGreater(len(context.diffbot_requests.all()), 0)

    def test_doPerformDiffBotRequest(self):
        """
        Should get text content, date, author.
        """
        
        doPerformDiffBotRequest(None, None, [self.diffbot_request])
        time.sleep(10)
        
        dbr = DiffBotRequest.objects.get(pk=self.diffbot_request.id)
        self.assertNotEqual(dbr.attempted, None)
        self.assertNotEqual(dbr.completed, None)
        self.assertGreater(len(dbr.response), 0)
        
    