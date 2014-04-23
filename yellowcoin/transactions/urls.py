from django.conf.urls import patterns, url
from yellowcoin.transactions.views import *

# c.f. http://bit.ly/IFquSV for url pattern matching with arguments; used in tranactions/views.py
urlpatterns = patterns('',
	url(r'^$', Index.as_view(), name='transactions|index'),
	url(r'^create$', TemplateView.as_view(template_name='transactions/create.html'), name='transactions|create')
)
