from django.shortcuts import render

from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from yellowcoin.api.fees.serializers import *
from yellowcoin.api.fees.models import *
from yellowcoin.enums import CURRENCIES, CRYPTOCURRENCIES
from django.utils import timezone

from decimal import Decimal

# get current market price for currencies
class GetFee(generics.RetrieveAPIView):
	permission_classes = ( AllowAny, )
	serializer_class = GetFeeSerializer
	def get(self, request, bid_currency, ask_currency, bid_val, ask_val):
		bid_currency = bid_currency.upper()
		ask_currency = ask_currency.upper()
		try:
			float(bid_val)
			float(ask_val)
		except ValueError:
			return Response({'status' : 400, 'detail' : 'Invalid values'}, status=400)
		try:
			serializer = GetFeeSerializer(Fee(bid_currency, ask_currency, bid_val, ask_val))
			return Response(serializer.data, status=200)
		except Exception as e:
			return Response({'status' : 500, 'detail' : 'An internal error occurred while trying to fetch the latest price.'}, status=500)
