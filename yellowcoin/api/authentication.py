from django.db.models.loading import get_model
from rest_framework import authentication
from rest_framework import exceptions

class YellowcoinAuthentication(authentication.BaseAuthentication):
	def authenticate(self, request):
		key = request.GET.get('key')
		if not key:
			return None
		APIKey = get_model('users', 'APIKey')
		try:
			api_key = APIKey.objects.get(key=key)
		except APIKey.DoesNotExist:
			raise exceptions.AuthenticationFailed('No such api key')
		if not api_key.user.use_api:
			raise exceptions.AuthenticationFailed('The user does not have API access enabled')
		return (api_key.user, None)
