from django.conf.urls import patterns, url
from django.views.generic import *
from yellowcoin.users.views import *
from yellowcoin.main.views import Contact

urlpatterns = patterns('',
	url(r'^about/$', TemplateView.as_view(template_name="main/about.html"), name='about'),
	url(r'^contact-us/$', Contact, name='contact'),
	url(r'^blog/$', RedirectView.as_view(url='http://blog.yellowco.in/'), name='blog'),
)
