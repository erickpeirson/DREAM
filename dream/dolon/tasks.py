@shared_task
def getStoreContext(url, itemid):
    """
    Retrieve the HTML contents of a resource and attach it to an :class:`.Item`
    
    Parameters
    ----------
    url : str
        Location of resource.
        
    Returns
    -------
    context.id : int
        ID for the :class:`.Context`
    """

    response = urllib2.urlopen(url).read()
    soup = BeautifulSoup(response)
#    text = p.html
    title = soup.title.getText()

    context = Context(  url = url,
                        title = title,
                        content = response  )
    context.save()
    
    item = Item.objects.get(id=itemid)
    item.context = context
    item.save()    
    
    return context.id
