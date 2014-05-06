from django.conf.urls import patterns, url
from yellowcoin.api.internal.views import *

urlpatterns = patterns('',
	url(r'^bank/lookup/(?P<routing_number>[0-9]{9})/$', LookupBankRoutingNumber.as_view(), name='internal|lookup-bank-routing-number'),
	url(r'^resend-validation-email/$', ResendValidationEmail.as_view(), name='internal|resend-validation-email')
)
