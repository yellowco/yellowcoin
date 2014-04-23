from django.views.generic import *
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import *

class Index(TemplateView):
	template_name = 'transactions/index.html'

	@method_decorator(login_required)
	def dispatch(self, request, *args, **kwargs):
		return super(Index, self).dispatch(request, *args, **kwargs)
