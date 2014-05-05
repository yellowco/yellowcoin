from django.db.models.loading import get_model
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework import authentication
from rest_framework import exceptions

class YellowcoinAuthentication(authentication.TokenAuthentication):
	def authenticate(self, request):
		self.model = get_model('users', 'APIKey')
		key = request.GET.get('key')
		if key:	
			return self.authenticate_credentials(key)
		else:
			return super(YellowcoinAuthentication, self).authenticate(request)
			
	def authenticate_credentials(self, key):
		try:
			api_key = self.model.objects.get(key=key, user__is_active=True)
		except self.model.DoesNotExist:
			raise exceptions.AuthenticationFailed('No such api key')
		if not api_key.user.use_api:
			raise exceptions.AuthenticationFailed('The user does not have API access enabled')
		return (api_key.user, api_key)
