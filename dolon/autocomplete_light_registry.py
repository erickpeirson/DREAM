import autocomplete_light

from models import *

autocomplete_light.register(Tag,
	search_fields=['text'],
)