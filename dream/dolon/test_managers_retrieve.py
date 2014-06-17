from django.test import TestCase
from managers import ImageRetriever
from models import Thumbnail, Image, Context
import json

thumburl = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRLchzhwk-ADaYkhcsRrdmKFYFo-g_cvqbFZMPaxNX6BeLAkuKb1x8RClk'
imageurl = 'http://wendycarrillo.files.wordpress.com/2010/11/antoine-dodsen-dream-act-3.jpg'
contexturl = 'http://wendycarrillo.wordpress.com/2010/11/24/fox-news-attacks-the-dream-act/'


#class TestImageRetriever(TestCase):
#    def setUp(self):
#        self.R = ImageRetriever()
#    
#    def test_retrieveThumbnail(self):
#        """
#        Should return a :class:`.Thumbnail` instance.
#        
#        TODO: check that a real image has been downloaded?
#        """
#
#        result = self.R.retrieveThumbnail(thumburl)
#        self.assertIsInstance(result, Thumbnail)
#        self.assertEqual(result.url, thumburl)
#        self.assertGreater(result.height, 0)
#        self.assertGreater(result.width, 0)
#        self.assertGreater(result.size, 0)
#        self.assertIsInstance(result.mime, str)
#        self.assertGreater(len(result.mime), 0)
#
#    def test_retrieveImage(self):
#        """
#        Should return a :class:`.Thumbnail` instance.
#        
#        TODO: check that a real image has been downloaded?
#        """
#
#        result = self.R.retrieveImage(imageurl)
#        self.assertIsInstance(result, Image)
#        self.assertEqual(result.url, imageurl)
#        self.assertGreater(result.height, 0)
#        self.assertGreater(result.width, 0)
#        self.assertGreater(result.size, 0)
#        self.assertIsInstance(result.mime, str)
#        self.assertGreater(len(result.mime), 0)
#
#    def test_retrieveContext(self):
#        """
#        Should return a :class:`.Context` instance.
#        """
#
#        result = self.R.retrieveContext(contexturl)
#
#        self.assertIsInstance(result, Context)
#        self.assertEqual(result.url, contexturl)
#        self.assertGreater(len(result.content), 0)
#        self.assertGreater(len(result.title), 0)
#
##class
#
#
#
## Create your tests here.
