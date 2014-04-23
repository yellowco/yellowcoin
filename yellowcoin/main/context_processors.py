from django.conf import settings
from django.contrib.sites.models import get_current_site

def current_protocol(request):
	return {'site_protocol': 'https://' if request.is_secure() else 'http://'}

def current_domain(request):
	return {'site_domain': get_current_site(request).domain}
