from django.conf.urls import patterns, include, url
from django.conf import settings
from django.views.generic import *
from django.contrib import admin
from yellowcoin.main.views import Dashboard, documentation
from yellowcoin.users.views import Referral

admin.autodiscover()

urlpatterns = patterns('',
	url(r'^$', TemplateView.as_view(template_name="main/index.html"), name='home'),
	url(r'^dashboard/.*$', Dashboard, name='application'),
	url(r'^grappelli/', include('grappelli.urls')),
	url(r'^admin/', include(admin.site.urls), name='admin'),

	url(r'^refer/(?P<referral_id>.+)/$', Referral, name='refer'),
	url(r'^users/', include('yellowcoin.users.urls')),
	url(r'^transactions/', include('yellowcoin.transactions.urls')),

	url(r'^api/$', documentation, name='documentation'),
	url(r'^api/', include('yellowcoin.api.urls')),
	url(r'^internal/', include('yellowcoin.api.internal.urls')),

	url(r'^', include('yellowcoin.main.urls')),
)
if settings.DEBUG:
	urlpatterns += patterns('',
		(r'^404/$', 'django.views.defaults.page_not_found')
	)
