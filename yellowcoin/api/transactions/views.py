from django.http import Http404
from django.db import transaction
from django.shortcuts import *
from django.views.generic import *
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework.exceptions import *
from rest_framework import generics
from yellowcoin.api.transactions.permissions import IsAuthenticatedOrReadOnly
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
import yellowcoin.users.signals
from yellowcoin.api.exceptions import *
from yellowcoin.api.transactions.serializers import *
from yellowcoin.currencypool.models import POOLS
from yellowcoin.users.models import *
from yellowcoin.transactions.models import Transaction, Order
from yellowcoin.enums import CRYPTOCURRENCIES, CURRENCIES
import time
import requests

from decimal import Decimal

# debug
from pprint import pformat

class ListTransactions(generics.ListAPIView):
	"""
	List all transactions.

	A transaction is the actual transfer of currency or cryptocurrency, whereas an order represents the actual exchange of currencies. Transaction also contains order metadata.
	GET comment <- The comment attached to the order e.g. Bitcoin for charity
	GET withdrawal_account <- The account the bid currency was drawn from e.g. qye2y67icpsskvwp
	GET deposit_account <- The account the ask currency was drawn from e.g. 3duwebqqjoqmo7np
	GET withdrawal_tx_id <- The transaction ID of the bid currency withdrawal e.g. 7235FE78-CB85-4230-A5BA-0793E5E1E0F9
	GET deposit_tx_id <- The transaction ID of the ask currency deposit e.g. 948f4004ce7cec15b24f0e8d5c6671b702aa0ec45f9694a80b4c6b754f572ddb
	"""
	permission_classes = ( IsAuthenticated, )
	serializer_class = TransactionSerializer
	paginate_by = 10
	max_paginate_by = 100

	def get_pagination_serializer(self, page, *args, **kwargs):
		# Strip away the pagination cruft
		return self.get_serializer(instance=page, many=True)

	def get_queryset(self):
		return Transaction.objects.filter_active(user=self.request.user)

class RetrieveTransactions(generics.RetrieveAPIView):
	permission_classes = (IsAuthenticated,)
	serializer_class = TransactionSerializer
	def get_object(self):
		try:
			return Transaction.objects.get(user=self.request.user, order__id=self.kwargs.get('pk', 0))
		except Transaction.DoesNotExist:
			raise Http404

class ListTransactionLimits(generics.ListAPIView):
	permission_classes = (IsAuthenticated,)
	serializer_class = TransactionLimitSerializer
	def get_queryset(self):
		return TransactionLimit.objects.filter(user=self.request.user)
	def get(self, request):
		return Response(self.request.user.get_all_limits(), status=200)

class ListCreateRecurringOrder(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated,)
	serializer_class = RecurringOrderSerializer
	def get_queryset(self):
		return RecurringOrder.objects.filter(user=self.request.user)
	def post(self, request):
		order = self.get_serializer(data=request.DATA)
		if order.is_valid():
			order.object.user = request.user
			order.save()
			return Response(order.data, status=201)
		raise GenericException(order.errors, status=400)

class RetrieveUpdateDestroyRecurringOrder(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated,)
	serializer_class = RecurringOrderSerializer
	def get_queryset(self):
		return RecurringOrder.objects.filter(user=self.request.user, id=self.kwargs.get('pk', 0))

class ListCreateOrderTemplates(generics.ListCreateAPIView):
	permission_classes = ( IsAuthenticated, )
	serializer_class = OrderTemplateSerializer

	def get_queryset(self):
		args = dict((k, v.upper()) for (k, v) in self.kwargs.items())
		return OrderTemplate.objects.filter(user=self.request.user, **args)

	def post(self, request, bid_currency='', ask_currency=''):
		if not bid_currency or not ask_currency:
			raise GenericException({'bid_currency':['Specify this field in the URL.'], 'ask_currency':['Specify this field in the URL.']}, status=400)
		data = request.DATA.copy()
		data['bid_currency'] = bid_currency.upper()
		data['ask_currency'] = ask_currency.upper()
		template = self.get_serializer(data=data)
		if template.is_valid():
			template.object.user = request.user
			template.save()
			return Response(template.data, status=201)
		raise GenericException(template.errors, status=400)

class RetrieveUpdateDestroyOrderTemplates(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = ( IsAuthenticated, )
	serializer_class = OrderTemplateSerializer
	def get_queryset(self):
		return OrderTemplate.objects.filter(user=self.request.user, id=self.kwargs.get('pk', 0))

class RetrieveDestroyOrder(generics.RetrieveDestroyAPIView):
	permission_classes = ( IsAuthenticatedOrReadOnly, )
	serializer_class = OrderSerializer

	def get_queryset(self):
		return Order.objects.get(id=self.kwargs.get('pk', 0), transaction__user=self.request.user)

	def get(self, request, pk):
		try:
			order = self.get_queryset()
		except Order.DoesNotExist:
			raise GenericException({}, status=404)
		if order.transaction.status in ('D', 'A'):
			raise GenericException({}, status=404)
		return Response(OrderSerializer(order).data, status=200)

	@transaction.atomic
	def delete(self, request, pk):
		try:
			order = self.get_queryset()
		except Order.DoesNotExist:
			raise GenericException({}, status=404)
		if order.transaction.status in ('D', 'A'):
			raise GenericException({}, status=404)
		if order.transaction.status not in ('U', 'I', 'P'):
			raise GenericException({}, status=405)
		order.transaction.status = 'D'
		order.transaction.save()
		return Response([], status=204)

# order fulfillment is handled exclusively by the task queue (yellowcoin/transactions/tasks.py)
class ListCreateOrder(generics.ListCreateAPIView):
	"""
	Retrieve or create an order request.

	<span class="label label-success">GET</span> <code>/api/orders/</code> - List an array of order objects

	<span class="label label-success">GET</span> <code>/api/orders/&lt;id&gt;/</code> - List a specific order

	<span class="label label-info">POST</span> <span class="label label-success">GET</span> <code>/api/orders/&lt;bid_currency&gt;/&lt;ask_currency&gt;/</code> - Place an order or list all orders associated with a currency pair

	<span class="label label-danger">DELETE</span> <span class="label label-success">GET</span> <code>/api/orders/&lt;id&gt;/</code> - Retrieve or delete (if possible) a specific order.

	The example represents a single order object.

	GET DELETE id -> The id of the order to retrieve e.g. ugkhw2113lz6e3ha
	POST bid_subtotal -> The amount to bid in exchange e.g. 1000
	POST ask_subtotal -> The amount asking in exchange e.g. 1
	GET POST bid_currency -> The currency of the bid e.g. USD
	GET POST ask_currency -> The currency of the ask e.g. BTC
	POST withdrawal_account -> The id of the account to draw the bid currency from e.g. ugkhw2113lz6e3ha
	POST deposit_account -> The id of the account to deposit the ask currency to e.g. ds4w6hicfv1cmlh5
	POST comment -> An optional comment associated with this order e.g. My first order

	GET POST id <- An id associated with this order e.g. ugkhw2113lz6e3ha
	GET bid_subtotal <- The amount bid for e.g. 1000
	GET ask_subtotal <- The amount asked for e.g. 1
	GET bid_currency <- The currency of the bid e.g. USD
	GET ask_currency <- The currency of the ask e.g. BTC
	GET bid_fee <- The fee associated with the bid currency e.g. 10
	GET ask_fee <- The fee associated with the ask currency e.g. 0
	GET exchange_rate <- bid_subtotal / ask_subtotal e.g. 1000
	GET POST timestamp <- The timestamp this order was placed at e.g. 2014-01-07T05:37:07.512Z
	"""
	permission_classes = ( IsAuthenticatedOrReadOnly, )
	serializer_class = OrderSerializer
	paginate_by = 10
	max_paginate_by = 100

	def get_queryset(self):
		args = dict([(k, v.upper()) for (k, v) in self.kwargs.items()])
		return Order.objects.filter(**args).filter(transaction__status='C')

	def get_pagination_serializer(self, page, *args, **kwargs):
		# Strip away the pagination cruft
		return self.get_serializer(instance=page, many=True)

	@transaction.atomic
	def post(self, request, bid_currency='', ask_currency=''):
		data = request.DATA.copy()
		data['bid_currency'] = bid_currency.upper()
		data['ask_currency'] = ask_currency.upper()

		template = None

		# handle one-click orders
		if 'one_click' in data and data['one_click']:
			template = request.user.one_click_order_template
		# duck-type the OrderTemplate POST request into an Order POST request
		if 'order_template' in data:
			try:
				template = OrderTemplate.objects.get(user=self.request.user, id=data['order_template'])
			except OrderTemplate.DoesNotExist:
				raise GenericException({'order_template' : [ 'Order template not found' ]}, status=400)
		
		if template:
			if bid_currency != '' or ask_currency != '':
				if template.bid_currency.upper() != bid_currency.upper() or template.ask_currency.upper() != ask_currency.upper():
					raise GenericException({'order_template':['Order template currencies do not match']}, status=400)
			try:
				data = Order.objects.create_data_from_template(template, data=data)
			except NotImplementedError:
				raise GenericException({ 'order_template' : [ 'Template improperly configured' ] }, status=400)
			except InsufficientFundsException:
				raise GenericException({'order_template': ['Automated orders cannot be created right now, please manually place a limit order.']}, status=400)
		if data['bid_currency'] == '' or data['ask_currency'] == '':
			raise GenericException({ 'non_field_errors' : [ 'invalid currencies' ] }, status=400)

		# ensure the exchange is between sane protocols (and definitely between a cryptocurrency and cash denomination)
		try:
			is_cash = Order.is_cash
			if (is_cash(data['bid_currency']) and is_cash(data['ask_currency'])) or (not is_cash(data['ask_currency']) and not is_cash(data['bid_currency'])):
				raise GenericException({ 'non_field_errors' : [ 'We do not support this transaction type at this time.' ] }, status=400)
		except BadProtocolException:
			raise GenericException({ 'non_field_errors' : [ 'Invalid currencies.' ] }, status=400)

		# cannot invoke with Serializer(request.DATA) because model is not provided
		#	cf. http://bit.ly/1cCHTXV
		serializer = self.get_serializer(data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=201)
		raise GenericException(serializer.errors, status=400)
