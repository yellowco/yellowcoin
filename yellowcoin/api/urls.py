from django.conf.urls import patterns, url
from yellowcoin.api.fees.views import *
from yellowcoin.api.prices.views import *
from yellowcoin.api.transactions.views import *
from yellowcoin.api.users.views import *

urlpatterns = patterns('',
	url(r'^profile/$', RetrieveUpdateProfile.as_view(), name='users|display-edit-profile'),
	url(r'^settings/$', RetrieveUpdateSettings.as_view(), name='users|retrieve-update-settings'),
	url(r'^limits/$', ListTransactionLimits.as_view()),
	url(r'^accounts/bank/$', ListCreateBankAccounts.as_view(), name='api|users|display-edit-bank-accounts'),
	url(r'^accounts/credit/$', ListCreateCreditCards.as_view(), name='api|users|display-edit-credit-cards'),
	url(r'^notifications/$', RetrieveUpdateNotifications.as_view(), name='api|users|retrieve-update-all-notifications'),
	url(r'^notifications/(?P<medium>[sms|email])/$', RetrieveUpdateNotifications.as_view(), name='api|users|retrieve-update-notifications'),
	url(r'^accounts/bank/(?P<id>[A-Za-z0-9\+\_\-\=]{16})/$', RetrieveUpdateDestroyBankAccount.as_view(), name='api|users|retrieve-destroy-bank-account'),
	url(r'^accounts/bank/(?P<id>[A-Za-z0-9\+\_\-\=]{16})/verify/$', ValidateBankAccount.as_view(), name='api|users|validate-bank-account'),
	url(r'^accounts/credit/(?P<id>[A-Za-z0-9\+\_\-\=]{16})/$', RetrieveUpdateDestroyCreditCard.as_view(), name='api|users|retrieve-destroy-credit-card'),
	url(r'^accounts/(?P<currency>[A-Za-z]{3})/$', ListCreateCryptoAccounts.as_view(), name='api|users|display-edit-crypto-accounts'),
	url(r'^accounts/(?P<currency>[A-Za-z]{3})/(?P<id>[A-Za-z0-9\+\_\-\=]{16})/$', RetrieveUpdateDestroyCryptoAccount.as_view(), name='api|user|retrieve-update-destroy-crypto-account'),
	url(r'^accounts/$', ListAccounts.as_view(), name='api|users|list-accounts'),
	url(r'^transactions/$', ListTransactions.as_view(), name='transactions|list-transactions'),
	url(r'^transactions/(?P<pk>[A-Za-z0-9\+\-\_\=]{16})/$', RetrieveTransactions.as_view()),
	url(r'^orders/$', ListCreateOrder.as_view(), name='transactions|list-create-order'),
	url(r'^orders/(?P<pk>[A-Za-z0-9\+\-\_\=]{16})/$', RetrieveDestroyOrder.as_view(), name='transactions|destroy-order'),
	url(r'^orders/(?P<ask_currency>[A-Za-z]{3})/(?P<bid_currency>[A-Za-z]{3})/$', ListCreateOrder.as_view(), name='transactions|list-create-order'),
	url(r'^orders/recurring/$', ListCreateRecurringOrder.as_view(), name='orders|recurring'),
	url(r'^orders/recurring/(?P<pk>[A-Za-z0-9\+\-\_\=]{16})/$', RetrieveUpdateDestroyRecurringOrder.as_view(), name='orders|recurring|view'),
	url(r'^orders/templates/$', ListCreateOrderTemplates.as_view(), name='orders|templates'),
	url(r'^orders/templates/(?P<ask_currency>[A-Za-z]{3})/(?P<bid_currency>[A-Za-z]{3})/$', ListCreateOrderTemplates.as_view()),
	url(r'^orders/templates/(?P<pk>[A-Za-z0-9\+\-\_\=]{16})/$', RetrieveUpdateDestroyOrderTemplates.as_view(), name='orders|templates|view'),
	url(r'^prices/(?P<ask_currency>[A-Za-z]{3})/(?P<bid_currency>[A-Za-z]{3})/$', GetPrice.as_view(), name='api|prices|get-price'),
	url(r'^fees/(?P<ask_currency>[A-Za-z]{3})/(?P<bid_currency>[A-Za-z]{3})/(?P<ask_val>\d*\.?\d*)/(?P<bid_val>\d*\.?\d*)/$', GetFee.as_view(), name='api|fees|get-fee')
)

