from django.contrib.auth.models import User

from django.test import TestCase
from tasks import spawnSearch
from search_managers import GoogleImageSearchManager
from models import QueryResult, Engine, QueryEvent, QueryString
import json

import cPickle as pickle
responsePickle = './dolon/testdata/searchresponse.pickle'
resultPickle = './dolon/testdata/searchresult.pickle'

apikey = "AIzaSyDhlbNOLTRRVebYs5PNx9snu6SZOsQFYnM"
cx = "002775406652749371248:l-zbbsqhcte"

cg_path = './dolon/callgraphs/'

class TestGoogleImageSearchManager(TestCase):
    def setUp(self):
        self.G = GoogleImageSearchManager()
        self.parameters =  [    "key={0}".format(apikey),
                                "cx={0}".format(cx) ]
        self.query = "dream act"

    def test_image_search(self):
        """
        Should return a string containing parseable JSON.
        """
        
        response = self.G.imageSearch(self.parameters, self.query)
        
        self.assertIsInstance(response,tuple, 'Response is not a tuple.')
        self.assertIsInstance(response[0], dict, 'Bad response value.')
        
#        with open(responsePickle, 'w') as f:
#            pickle.dump(response[1], f)
#        with open(resultPickle, 'w') as f:
#            pickle.dump(response[0], f)

    def test_handle_result(self):
        """
        """

        with open('./dolon/testdata/testresponse.json', 'r') as f:
            response = f.read()
        
        qr, qi = self.G._handleResponse(response)

        self.assertIsInstance(qr, dict, 'Bad response value.')
        self.assertIsInstance(qi, dict, 'Bad response value.')
        self.assertEqual(qr['items'][0]['type'], 'image')

