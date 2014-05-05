from django.conf.urls import patterns, include, url
from yellowcoin.users.views import *

urlpatterns = patterns('',
	url(r'^verify/$', Verify, name='users|verify'),
	url(r'^reset-password/$', ResetPassword.as_view(), name='users|reset-password'),
	url(r'^reset-password/(?P<key>[A-Za-z0-9\+\-\_\=]{16})/$', ResetPassword.as_view(), name='users|reset-password'),
	# url(r'^reset-phone/$', ResetPhone, name='users|reset-phone'),
	url(r'^login/$', Login, name='users|login'),
	url(r'^logout/$', Logout, name='users|logout'),
	url(r'^register/$', RegisterUser.as_view(), name='users|register'),
	url(r'^activate/$', ActivateUser.as_view(), name='users|activate-manual'),
	url(r'^activate/([A-Za-z0-9]+)/$', 'yellowcoin.users.views.activate', name='users|activate'),
)
