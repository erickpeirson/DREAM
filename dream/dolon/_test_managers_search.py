from django.test import TestCase
from managers import GoogleImageSearchManager, spawnSearch
from models import QueryResult, QueryItem, Engine, QueryEvent, QueryString
import json

from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput

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
        
        with PyCallGraph(output=GraphvizOutput(
                output_file=cg_path + 'managers.GoogleImageSearchManager.imageSearch.png')):
            response = self.G.imageSearch(self.parameters, self.query)

        self.assertIsInstance(response,str, 'Response is not a string.')
        self.assertGreater(len(response), 0, 'Response is empty')

        raised = False
        try:
            rjson = json.loads(response)
        except:
            raised = True
        self.assertFalse(raised, 'Exception raised.')

    def test_handle_result(self):
        """
        Should return a :class:`.QueryResult` instance and a list of
        :class:`.QueryItem` instances.
        """

        with open('./dolon/testdata/testresponse.json', 'r') as f:
            response = f.read()
        
        with PyCallGraph(output=GraphvizOutput(
                output_file=cg_path + 'managers.GoogleImageSearchManager.handleResults.png')):
            qr, qi = self.G.handleResults(response)

        self.assertIsInstance(qr, QueryResult)
        self.assertIsInstance(qi, list)
        self.assertIsInstance(qi[0], QueryItem)

class TestSearch(TestCase):
    def test_spawnSearch(self):
        """
        A query with range of 20 should return 2 QueryResults of 10 QueryItems
        each. Each QueryItem should have a Thumbnail associated with it.
        """
        
        QS = QueryString(   querystring = 'dream act'   )
        QS.save()
        E = Engine( parameters = [  "key={0}".format(apikey),
                                    "cx={0}".format(cx) ],
                    manager = 'GoogleImageSearchManager'    )
        E.save()
        QE = QueryEvent(    querystring = QS,
                            rangeStart = 1,
                            rangeEnd = 20,
                            engine = E  )
        QE.save()

        with PyCallGraph(output=GraphvizOutput(
                output_file=cg_path + 'managers.spawnSearch.png')):
            result = spawnSearch(QE)

        res = result.queryresults.all()
        
        self.assertEqual(len(res), 2, 'Too few QueryResults')
        for r in res:
            items = r.items.all()
            self.assertEqual(len(items), 10, 'Too few QueryItems')
            for i in items:
                self.assertIsNot(i.thumbnail, None, 'Thumbnail not attached.')

