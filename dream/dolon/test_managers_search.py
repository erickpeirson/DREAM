from django.contrib.auth.models import User

from django.test import TestCase
from tasks import spawnSearch
from search_managers import *
from models import *
import datetime
import json

import cPickle as pickle
responsePickle = './dolon/testdata/searchresponse.pickle'
resultPickle = './dolon/testdata/searchresult.pickle'

apikey = "AIzaSyDhlbNOLTRRVebYs5PNx9snu6SZOsQFYnM"
cx = "002775406652749371248:l-zbbsqhcte"

cg_path = './dolon/callgraphs/'

#class TestGoogleImageSearchManager(TestCase):
#    def setUp(self):
#        self.G = GoogleImageSearchManager()
#        self.parameters =  [    "key={0}".format(apikey),
#                                "cx={0}".format(cx) ]
#        self.query = "dream act"
#
#    def test_image_search(self):
#        """
#        Should return a string containing parseable JSON.
#        """
#        
#        response = self.G.imageSearch(self.parameters, self.query)
#        
#        self.assertIsInstance(response,tuple, 'Response is not a tuple.')
#        self.assertIsInstance(response[0], dict, 'Bad response value.')
#        
##        with open(responsePickle, 'w') as f:
##            pickle.dump(response[1], f)
##        with open(resultPickle, 'w') as f:
##            pickle.dump(response[0], f)
#
#    def test_handle_result(self):
#        """
#        """
#
#        with open('./dolon/testdata/testresponse.json', 'r') as f:
#            response = f.read()
#        
#        qr, qi = self.G._handleResponse(response)
#
#        self.assertIsInstance(qr, dict, 'Bad response value.')
#        self.assertIsInstance(qi, dict, 'Bad response value.')
#        self.assertEqual(qr['items'][0]['type'], 'image')

class TestInternetArchiveManager(TestCase):
    def setUp(self):
        self.G = InternetArchiveManager()
        self.query = '"dream act"'
        
#    def test_query(self):
#        self.G.search([], self.query, 0, 10)

#    def test_handleResponse(self):
#        self.G._handleResponse()
#
#    def test_getDetails_audio(self):
#        identifier = "Insight_101214"
#        request, dp, c, desc, files = self.G._getDetails(identifier, 'audio')
#        expected = 'https://archive.org/details/Insight_101214&output=json'
#
#        self.assertEqual(request, expected)
#
#        self.assertIsInstance(dp, datetime.datetime)
#        self.assertEqual(dp.year, 2010)
#        self.assertEqual(dp.month, 12)
#        self.assertEqual(dp.day, 14)        
#
#        self.assertEqual(c, 'johnb@csus.edu')
#                
#        self.assertIsInstance(desc, str)
#        self.assertGreater(len(desc), 0)
#        
#        expected = [    'http://ia600309.us.archive.org/31/items/Insight_101214/Insight_101214.wav', 
#                        'http://ia600309.us.archive.org/31/items/Insight_101214/Insight_101214.mp3', 
#                        'http://ia600309.us.archive.org/31/items/Insight_101214/Insight_101214.flac', 
#                        'http://ia600309.us.archive.org/31/items/Insight_101214/Insight_101214.ogg'  ]
#        self.assertEqual(files, expected)
#                
#
#    def test_parseFilemeta(self):
#        """
#        should return a list of remote audio files.
#
#        e.g. see http://ia600309.us.archive.org/31/items/Insight_101214/Insight_101214_files.xml
#        """
#
#        with open('./dolon/testdata/tmp_filemeta.xml', 'r') as f:
#            filemeta_content = pickle.load(f)
#        baseurl = 'test/'
#        
#        audiofiles = self.G._parseFilemeta(baseurl, filemeta_content, 'audio')
#
#        expected = [    'test/Insight_101214.wav', 'test/Insight_101214.mp3', 
#                        'test/Insight_101214.flac', 'test/Insight_101214.ogg'  ]
#        self.assertEqual(audiofiles, expected)
#        
#    def test_parseMetacontent(self):
#        """
#        should return publication date, creator, and description.
#        
#        e.g. see http://ia600309.us.archive.org/31/items/Insight_101214/Insight_101214_meta.xml
#        """
#
#        with open('./dolon/testdata/tmp_meta_content.xml', 'r') as f:
#            meta_content = pickle.load(f)
#        baseurl = 'test/'
#        
#        dp, creator, desc = self.G._parseMetacontent(baseurl, meta_content)
#        
#        self.assertIsInstance(dp, datetime.datetime)
#        self.assertEqual(dp.year, 2010)
#        self.assertEqual(dp.month, 12)
#        self.assertEqual(dp.day, 14)
#        
#        self.assertIsInstance(creator, str)
#        self.assertEqual(creator, 'johnb@csus.edu')
#        
#        self.assertIsInstance(desc, str)
#        self.assertGreater(len(desc), 0)
        