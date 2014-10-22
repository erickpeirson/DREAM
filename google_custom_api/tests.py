from django.test import TestCase
from google_custom_api.models import GoogleQueryEvent
from google_custom_api.managers import GoogleSearchManager
import dolon

class SearchCase(TestCase):
    def setUp(self):
        # Create a QueryString to search with.
        self.querystring = dolon.models.QueryString(
                                            querystring='dream act'
                                            )
        self.querystring.save()
        
        # Create a QueryEvent.
        self.queryevent = GoogleQueryEvent(
                            querystring=self.querystring,
                            start=1,
                            num=10,
                            )
        self.queryevent.save()
        self.manager = GoogleSearchManager()
        
    def test_search(self):
        self.manager.search(self.queryevent.id)