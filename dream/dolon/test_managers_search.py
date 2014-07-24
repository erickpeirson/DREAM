from django.contrib.auth.models import User

from django.test import TestCase
from tasks import GoogleImageSearchManager, spawnSearch
from models import QueryResult, Engine, QueryEvent, QueryString
import json

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

    def test_handle_result(self):
        """
        Should return a :class:`.QueryResult` instance and a list of
        :class:`.QueryItem` instances.
        """

        with open('./dolon/testdata/testresponse.json', 'r') as f:
            response = f.read()
        

        qr, qi = self.G._handleResponse(response)

        self.assertIsInstance(qr, dict, 'Bad response value.')
        self.assertIsInstance(qi, dict, 'Bad response value.')        

