from django.test import TestCase
from ..tasks import *
from ..models import DiffBotRequest, Context
from dream.settings import DIFFBOT_TOKEN
from pprint import pprint

test_url = 'http://www.masslive.com/news/index.ssf/2014/08/incoming_bishop_backs_need_for.html'

class TestDiffBotRequest(TestCase):
    def setUp(self):
        self.context = Context(url=test_url)
        self.context.save()
        
#    def test_createDiffBotRequest(self):
#        request = createDiffBotRequest('article', test_url)
#        expected_parameters = ['url={0}'.format(test_url), 'type=article']
#        self.assertEqual(request.parameters, expected_parameters)
#
#    def test_spawnRetrieveContexts(self):
#        spawnRetrieveContexts([self.context])
#        expected_parameters = ['url={0}'.format(test_url), 'type=article']        
#        self.assertEqual(   self.context.diffbot_requests.all()[0].parameters,
#                            expected_parameters )
#                            
#    def test_performDiffBotRequest(self):
#        spawnRetrieveContexts([self.context])
#        request = self.context.diffbot_requests.all()[0]
#        performDiffBotRequest(request)
#        
#        request = self.context.diffbot_requests.all()[0]
#        self.assertNotEqual(request.attempted, None)
#        self.assertNotEqual(request.completed, None)
#        
#        context = Context.objects.get(pk=self.context.id)
#        self.assertNotEqual(context.author, None)
#        self.assertNotEqual(context.text_content, None)
#        self.assertNotEqual(context.publicationDate, None)
#        self.assertNotEqual(context.title, None)
#        
    def test_trigger_diffbot_requests(self):
        request = createDiffBotRequest('article', test_url)
        request2 = createDiffBotRequest('article', test_url)        
        spawnRetrieveContexts([self.context])
        
        trigger_diffbot_requests()
        
        # Gets response and sets completed.
        request_ = DiffBotRequest.objects.get(pk=request.id)
        self.assertNotEqual(request_.completed, None)
        self.assertNotEqual(request_.response, None)
        
        # If a Context is associated with a request then it gets updated, too.
        context_ = Context.objects.get(pk=self.context.id)
        self.assertNotEqual(context_.publicationDate, None)
        
        