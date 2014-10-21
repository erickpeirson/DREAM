from django.db import models
import dolon

from . import choices

optional = {
    'blank':True,
    'null':True,
    }

class QueryEvent(dolon.models.QueryEvent):
    """
    Docstrings are based on the `Google Custom Search JSON API documentation
    <https://developers.google.com/custom-search/json-api/v1/reference/cse/list>`_.
    """
    
    @property
    def q(self):
        """
        The search expression.
        """
        return self.querystring.querystring

    searchType = models.CharField(
                    max_length=5, choices=choices.searchType_choices,
                    **optional)
    """
    Specifies the search type: image.  If unspecified, results are limited to
    webpages. 

    Acceptable values are:
    * "image": custom image search.
    """                    
    searchType.verbose_name = 'search type'
    searchType.help_text = 'If unspecified, results are limited to webpages.' 

    start = models.IntegerField(default=1)
    """
    The index of the first result to return.
    """    
    start.verbose_name = 'start at'
    start.help_text = 'The index of the first result to return.'

    num = models.IntegerField(**optional)
    """
    Number of search results to return.

    * Valid values are integers between 1 and 10, inclusive.    
    """
    num.verbose_name = 'number of results'
    num.help_text = 'Valid values are integers between 1 and 10, inclusive.'

    
    cr = models.CharField(max_length=9, choices=choices.cl_choices, **optional)
    """
    Restricts search results to documents originating in a particular country. 
    
    * You may use Boolean operators in the cr parameter's value.
    * Google Search determines the country of a document by analyzing:
      * the top-level domain (TLD) of the document's URL
      * the geographic location of the Web server's IP address
    * See the Country Parameter Values page for a list of valid values for this
      parameter.
      
    """
    cr.verbose_name = 'country'
    cr.help_text = 'Restricts search results to documents originating in a' +\
                   ' particular country.'
                   
    gl = models.CharField(max_length=2, choices=choices.gl_choices, **optional)
    """
    Geolocation of end user. 

    * The gl parameter value is a two-letter country code. The gl parameter
      boosts search results whose country of origin matches the parameter value.
      See the Country Codes page for a list of valid values.
    * Specifying a gl parameter value should lead to more relevant results.
      This is particularly true for international customers and, even more
      specifically, for customers in English- speaking countries other than the
      United States.
      
    """    
    gl.verbose_name = 'Geolocation'
    gl.help_text = 'Geolocation of end user. Boosts search results whose'+\
                   ' country of origin matches the parameter value.'

    lr = models.CharField(max_length=10, choices=choices.lr_choices, **optional)
    """
    Restricts the search to documents written in a particular language
    (e.g., lr=lang_ja).
    """
    lr.verbose_name = 'language'
    lr.help_text = 'Restricts the search to documents written in a particular'+\
                   ' language.'    
    
    hl = models.CharField(max_length=2, choices=choices.hl_choices, **optional)
    """
    Sets the user interface language. 
    
    * Explicitly setting this parameter improves the performance and the quality
      of your search results.
    * See the Interface Languages section of Internationalizing Queries and 
      Results Presentation for more information, and Supported Interface
      Languages for a list of supported languages.
      
    """    
    hl.verbose_name = 'user interface language'
    hl.help_text = 'Explicitly setting this parameter improves the'+\
                   ' performance and the quality of your search results. See'+\
                   ' the <a href="https://developers.google.com/custom-search'+\
                   '/docs/xml_results#wsInterfaceLanguages" target="_blank">'+\
                   'Interface Languages</a> section of <a href="https://devel'+\
                   'opers.google.com/custom-search/docs/xml_results#wsInterna'+\
                   'tionalizing" target="_blank">Internationalizing Queries' +\
                   ' and Results Presentation</a> for more information.'
    
    googlehost = models.CharField(max_length=12, **optional)
    """
    The local Google domain (for example, google.com, google.de, or google.fr)
    to use to perform the search. 
    """
    googlehost.verbose_name = 'google domain'
    googlehost.help_text = 'The local Google domain (for example, google.com,'+\
                           ' google.de, or google.fr) to use to perform the'  +\
                           ' search.'                   
    
    cref = models.URLField(max_length=255, **optional)
    """
    The URL of a linked custom search engine specification to use for this
    request. 
    
    * Does not apply for Google Site Search
    * If both cx and cref are specified, the cx value is used
        
    """
    cref.verbose_name = 'custom search URL'
    cref.help_text = 'The URL of a linked custom search engine specification' +\
                     ' to use for this request.'
    
    cx = models.CharField(max_length=255, **optional)
    """
    The custom search engine ID to use for this request.
    
    * If both cx and cref are specified, the cx value is used.
    
    """
    
    dateRestrict_value = models.IntegerField(**optional)
    """
    Restricts results to URLs based on date.
    """
    
    dateRestrict_by = models.CharField(
                                max_length=1, 
                                choices=choices.dateRestrict_choices,
                                **optional)
    """
    Restricts results to URLs based on date.
    """
        
    exactTerms = models.ForeignKey(
                        'dolon.QueryString', related_name='google_exactTerms',
                        **optional)
    """
    Identifies a phrase that all documents in the search results must contain.
    """
    exactTerms.verbose_name = 'must contain'
    exactTerms.help_text = 'Identifies a phrase that all documents in the' +\
                           ' search results must contain.'
                           
    excludeTerms = models.ForeignKey(
                            'dolon.QueryString', 
                            related_name='google_excludeTerms',
                            **optional)
    """
    Identifies a word or phrase that should not appear in any documents in the
    search results.
    """    
    excludeTerms.verbose_name = 'must not contain'
    excludeTerms.help_text = 'Identifies a word or phrase that should not' +\
                             ' appear in any documents in the search results.'
                             
    hq = models.ManyToManyField('dolon.QueryString', **optional)
    """
    Appends the specified query terms to the query, as if they were combined
    with a logical AND operator.
    """
    hq.verbose_name = 'extra AND terms'
    hq.help_text = 'Appends the specified query terms to the query, as if' +\
                   ' they were combined with a logical AND operator.'
    
    orTerms = models.ManyToManyField(
                        'dolon.QueryString', related_name='google_orTerms',
                        **optional)
    """
    Provides additional search terms to check for in a document, where each
    document in the search results must contain at least one of the additional
    search terms.
    """
    orTerms.verbose_name = 'extra OR terms'
    orTerms.help_text = 'Provides additional search terms to check for in a'+\
                        ' document, where each document in the search results'+\
                        ' must contain at least one of the additional search'+\
                        ' terms.'                                 
    
    fileType = models.CharField(max_length=10, **optional)
    """
    Restricts results to files of a specified extension. A list of file types
    indexable by Google can be found in Webmaster Tools Help Center.    
    """
    fileType.verbose_name = 'file type'
    fileType.help_text = 'Restricts results to files of a specified ' +\
                         'extension. A list of file types indexable by Google'+\
                         ' can be found in <a href="https://support.google.co'+\
                         'm/webmasters/answer/35287?hl=en" target="_blank">We'+\
                         'bmaster Tools Help Center</a>.'
    
    filter = models.BooleanField(default=True)
    """
    Controls turning on or off the duplicate content filter.
    
    * See Automatic Filtering for more information about Google's search results
      filters. Note that host crowding filtering applies only to multi-site 
      searches.
    * By default, Google applies filtering to all search results to improve the
      quality of those results.

    Acceptable values are:
    * "0": Turns off duplicate content filter.
    * "1": Turns on duplicate content filter.
    
    """
    filter.verbose_name = 'automatic filtering'
    filter.help_text = 'If enabled, filters search results to improve the'+\
                       ' quality of results. See <a href="https://developers.'+\
                       'google.com/custom-search/docs/xml_results#automaticFi'+\
                       'ltering" target="_blank">Automatic Filtering</a> for'+\
                       ' more information.'

    lowRange = models.IntegerField(**optional)
    """
    Specifies the starting value for a search range. 

    Use ``lowRange`` and ``highRange`` to append an inclusive search range of 
    ``lowRange...highRange`` to the query.
    """    
    lowRange.verbose_name = 'low range'
    lowRange.help_text = 'Use <strong>low range</strong> and <strong>' +\
                          'high range</strong> to append an inclusive search'+\
                          ' range of <strong>low range</strong>...<strong>'+\
                          'high range</strong>  to the query.'   
    
    highRange = models.IntegerField(**optional)
    """
    Specifies the ending value for a search range.

    Use ``lowRange`` and ``highRange`` to append an inclusive search range of 
    ``lowRange...highRange``  to the query.
    """
    highRange.verbose_name = 'high range'
    highRange.help_text = 'Use <strong>low range</strong> and <strong>' +\
                          'high range</strong> to append an inclusive search'+\
                          ' range of <strong>low range</strong>...<strong>'+\
                          'high range</strong>  to the query.'
    
    

    
    imgColorType = models.CharField(
                            max_length=5, choices=choices.imgColorType_choices,
                            **optional)
    """
    Returns black and white, grayscale, or color images: mono, gray, and color. 

    Acceptable values are:
    * "color": color
    * "gray": gray
    * "mono": mono
    
    """
    imgColorType.verbose_name = 'image color type'
    imgColorType.help_text = 'Returns black and white, grayscale, or color'+\
                             ' images.'
    
    imgDominantColor = models.CharField(
                                max_length=6,
                                choices=choices.imgDominantColor_choices,
                                **optional)
    """
    Returns images of a specific dominant color. 

    Acceptable values are:
    * "black": black
    * "blue": blue
    * "brown": brown
    * "gray": gray
    * "green": green
    * "pink": pink
    * "purple": purple
    * "teal": teal
    * "white": white
    * "yellow": yellow
    
    """
    imgDominantColor.verbose_name = 'dominant color type'
    imgDominantColor.help_text = 'Returns images of a specific dominant color.'
    
    imgSize = models.CharField(
                        max_length=7, choices=choices.imgSize_choices,
                        **optional)
    """
    Returns images of a specified size. 

    Acceptable values are:
    * "huge": huge
    * "icon": icon
    * "large": large
    * "medium": medium
    * "small": small
    * "xlarge": xlarge
    * "xxlarge": xxlarge
    """
    imgSize.verbose_name = 'image size'
    imgSize.help_text = 'Returns images of a specified size.'
    
    imgType = models.CharField(
                        max_length=7, choices=choices.imgType_choices,
                        **optional)
                        
    """
    Returns images of a type. 

    Acceptable values are:
    * "clipart": clipart
    * "face": face
    * "lineart": lineart
    * "news": news
    * "photo": photo
    """    
    imgType.verbose_name = 'image type'
    imgType.help_text = 'Returns images of a particular type.'
    
    linkSite = models.URLField(max_length=255, **optional)
    """
    Specifies that all search results should contain a link to a particular URL.
    """
    linkSite.verbose_name = 'containing link to'
    linkSite.help_text = 'Limit results to pages containing a link to this URL.'
    
    relatedSite = models.URLField(max_length=255, **optional)
    """
    Specifies that all search results should be pages that are related to the 
    specified URL.
    """    
    relatedSite.verbose_name = 'related to'
    relatedSite.help_text = 'Return results form pages that are related to'+\
                            ' the specified URL.' 
                            
    siteSearch = models.URLField(max_length=255, **optional)
    """
    Specifies all search results should be pages from a given site.
    """
    siteSearch.verbose_name = 'from site'
    siteSearch.help_text = 'Limit search to pages from the sitea at this URL.'
    
    siteSearchFilter = models.CharField(
                                max_length=1, 
                                choices=choices.siteSearchFilter_choices,
                                **optional)
    """
    Controls whether to include or exclude results from the site named in the
    siteSearch parameter. 

    Acceptable values are:
    * "e": exclude
    * "i": include
    """
    siteSearchFilter.verbose_name = 'from site behavior'
    siteSearchFilter.help_text = 'Controls whether to include or exclude'+\
                                 ' results from the site named in the'+\
                                 ' <strong>from site</strong> field.'
    
    rights = models.CharField(max_length=255, **optional)
    """
    Filters based on licensing. Supported values include: ``cc_publicdomain``,
    ``cc_attribute``, ``cc_sharealike``, ``cc_noncommercial``,
    ``cc_nonderived``, and combinations of these.
    """
    rights.help_text = 'Filters based on licensing. Supported values include:'+\
                       ' cc_publicdomain, cc_attribute, cc_sharealike,'+\
                       ' cc_noncommercial, cc_nonderived, and combinations'+\
                       ' of these.'
    
    safe = models.CharField(
                    max_length=6, choices=choices.safe_choices, default='off')
    """
    Search safety level. 

    Acceptable values are:
    * "high": Enables highest level of SafeSearch filtering.
    * "medium": Enables moderate SafeSearch filtering.
    * "off": Disables SafeSearch filtering. (default)
    """    
    safe.verbose_name = 'safe search'
    
    sort = models.CharField(max_length=255, **optional)
    """
    The sort expression to apply to the results.
    """
    sort.help_text = 'The sort expression to apply to the results.'

    c2coff = models.BooleanField(default=True)
    """
    Enables or disables Simplified and Traditional Chinese Search. 

    * The default value for this parameter is 0 (zero), meaning that the feature
      is enabled. Supported values are:
      * 1: Disabled
      * 0: Enabled (default)
    
    """
    c2coff.verbose_name = 'chinese'
    c2coff.help_text = 'Enables Simplified and Traditional Chinese Search.'
    