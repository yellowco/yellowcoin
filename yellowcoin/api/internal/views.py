from django.db import transaction
from django.shortcuts import *
from django.views.generic import *
from rest_framework.authentication import SessionAuthentication
from rest_framework import generics, serializers
from rest_framework.permissions import *
from rest_framework.response import Response
from django_routing_numbers import Institution
import requests

class LookupBankRoutingNumber(generics.RetrieveAPIView):
	authentication_classes = (SessionAuthentication,)
	permission_classes = ( IsAuthenticated, )
	serializer_class = serializers.Serializer
	def get(self, request, routing_number):
		try:
			name = Institution.objects.get(routing_number=routing_number).customer_name
		except Institution.DoesNotExist:
			name = 'Unknown'
		return Response({'name':name}, status=200)	
