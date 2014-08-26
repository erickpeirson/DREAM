from django.test import TestCase
from ..services import *
from dream.settings import DIFFBOT_TOKEN
from pprint import pprint

test_url = 'http://www.masslive.com/news/index.ssf/2014/08/incoming_bishop_backs_need_for.html'

class TestDiffBot(TestCase):
    def setUp(self):
        self.manager = DiffBotManager(DIFFBOT_TOKEN)

    def test_prep_request(self):
        params = self.manager.prep_request('article', test_url)
        expected = ['url={0}'.format(test_url), 'type=article']
        self.assertEqual(params, expected)
        
    def test_get_article(self):
        result = self.manager.get_article(test_url)
        
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)
        