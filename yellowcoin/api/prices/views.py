from django.shortcuts import render

from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from yellowcoin.currencypool.models import *
from yellowcoin.api.prices.serializers import *
from yellowcoin.api.prices.models import *
from yellowcoin.currencypool.models import POOLS
from yellowcoin.enums import CURRENCIES, CRYPTOCURRENCIES
from django.utils import timezone

from decimal import localcontext

# get current market price for currencies
class GetPrice(generics.RetrieveAPIView):
	"""
	Get the current price for a currency pair

	GET bid_currency -> The currency offering in exchange e.g. USD
	GET ask_currency -> The currency to exchange for e.g. BTC

	GET bid_currency <- Echoed from url e.g. USD
	GET ask_currency <- Echoed from url e.g. BTC
	GET price <- The price for one unit of bid_currency in units of ask_currency e.g. 1000
	GET timestamp <- The current timestamp e.g. 2014-01-10T14:07:45.286Z
	"""
	permission_classes = ( AllowAny, )
	serializer_class = GetPriceSerializer
	def get(self, request, bid_currency, ask_currency):
		bid_currency = bid_currency.upper()
		ask_currency = ask_currency.upper()
		try:
			with localcontext() as ctx:
				ctx.prec = 2 # round decimals
				price = Price(bid_currency, ask_currency, POOLS[getattr(CURRENCIES + CRYPTOCURRENCIES, bid_currency)][getattr(CURRENCIES + CRYPTOCURRENCIES, ask_currency)].get_bid_price(), timezone.now())
				serializer = GetPriceSerializer(price)
				return Response(serializer.data, status=200)
		except Exception as e:
			return Response({'status' : 500, 'detail' : 'An internal error occurred while trying to fetch the latest price.'}, status=500)
