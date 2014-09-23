from django.shortcuts import render, render_to_response
from dream import settings
from models import *
import random

def home(request):
    N_images = ImageItem.objects.all().count()
    N_audio = AudioItem.objects.all().count()
    N_videos = VideoItem.objects.all().count()
    N_texts = TextItem.objects.all().count()
    
    I = [ i for i in ImageItem.objects.all() if i.status == u'AP' and i.retrieved and list(i.images.all())[0].image.name != u'' ]
    bodybackground = list(I[random.randint(0,len(I)-1)].images.all())[0].image.url
    
    context = {
        'splash_title': settings.SITE_TITLE,
        'splash_subtitle': settings.SITE_TAGLINE,
        'dolon_version': settings.VERSION,
        'N_images': N_images,
        'N_audio': N_audio,
        'N_videos': N_videos,
        'N_texts': N_texts,
        'host': request.get_host(),
        'title': settings.SITE_TITLE,
        'bodybackground': bodybackground,
    }
        
    return render_to_response('splash.html', context)
    
