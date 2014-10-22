from django.test import TestCase
from google_custom_api.models import GoogleQueryEvent, GoogleEngine
from google_custom_api.managers import GoogleSearchManager
import dolon

apikey = "AIzaSyDhlbNOLTRRVebYs5PNx9snu6SZOsQFYnM"
cx = "002775406652749371248:l-zbbsqhcte"

class SearchCase(TestCase):
    def setUp(self):
        # Create a QueryString to search with.
        self.querystring = dolon.models.QueryString(
                                            querystring='dream act'
                                            )
        self.querystring.save()
        
        self.engine = GoogleEngine(
                        name = 'TestEngine',
                        cx = cx,
                        api_key = apikey,
                        )
        self.engine.save()
        
        # Create a QueryEvent.
        self.queryevent = GoogleQueryEvent(
                            querystring=self.querystring,
                            engine=self.engine,
                            start=1,
                            num=10,
                            )
        self.queryevent.save()
        self.manager = GoogleSearchManager()
        
    def test_search(self):
        self.manager.search(self.queryevent.id)