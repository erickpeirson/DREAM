from django.test import TestCase

from ..tasks import *
from ..models import *
from ..admin import *
from django.contrib.auth.models import User
from django.core.files import File

import celery
from celery.result import AsyncResult, TaskSetResult
import time
import cPickle as pickle

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

class TestApprove(TestCase):
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
    
        qr_id, q_I = processSearch( (searchResult_ia,searchResponse_ia), 
                                    self.queryevent.id  )
                                    
    def test_approve(self):
        queryset = Item.objects.all()[0:2]
        approve(None, None, queryset)
        
        afteritems = Item.objects.all()
        for item in afteritems:
            if hasattr(item, 'audioitem'):
                print [ i.audio_file for i in item.audioitem.audio_segments.all() ]
                
        self.assertEqual(0,1)
        