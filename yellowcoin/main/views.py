from django.contrib import messages
from django.conf import settings
from django.contrib.auth import *
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import *
from django.shortcuts import *
from django.views.generic import *
from django_rest_framework_docs_yellowcoin.rest_framework_docs.docs import DocumentationGenerator
from yellowcoin.api.users.views import RetrieveUpdateNotifications
from yellowcoin.api.users.serializers import BankAccountSerializer, CryptoAccountSerializer, ProfileSerializer, SettingSerializer, LoginRecordSerializer
from yellowcoin.api.transactions.serializers import TransactionSerializer, RecurringOrderSerializer
from template_email import TemplateEmail
from yellowcoin.users.models import CryptoAccount
import binascii, json
from yellowcoin.users.models import User, APIKey
from yellowcoin.crypto import base36encode
from django import forms
from yellowcoin.enums import CRYPTOCURRENCIES

def documentation(request):
	if request.method == 'POST' and request.user.is_authenticated():
		# user is requesting a new API key
		if 'delete' in request.POST:
			try:
				APIKey.objects.get(user=request.user, key=request.POST.get('delete','')).delete()
			except:
				pass
		else:
			APIKey.objects.create(user=request.user, comment=request.POST.get('comment','')).save()
		return redirect('documentation')
	docs = DocumentationGenerator().get_docs(as_objects=True)
	for doc in docs:
		doc.short_description = doc.description.split('<br/>')[0] if doc.description else ''
	# cf. http://bit.ly/1hwcLgH
	return render(request, 'main/docs.html', {'docs':enumerate(docs), 'keys':APIKey.objects.filter(user=request.user.id)})

def index(request):
	user_count = User.objects.count()
	if settings.MAX_USERS == -1:
		lock = False
	else:
		lock = user_count >= settings.MAX_USERS
	return render(request, 'main/index.html', {'lock':lock})

class ContactForm(forms.Form):
	subject = forms.CharField(max_length=100)
	message = forms.CharField()
	sender = forms.EmailField()

def Contact(request):
	if request.method == 'POST':
		form = ContactForm(request.POST)
		if form.is_valid():
			if send_mail(form.cleaned_data['subject'], form.cleaned_data['message'], form.cleaned_data['sender'], recipient_list=['help@yellowco.in'], fail_silently=True):
				messages.success(request, 'Thanks, we\'ll be in touch shortly!')
			else:
				messages.error(request, 'Uh oh, something went wrong. Please email us directly at help@yellowco.in, sorry!')
	else:
		form = ContactForm()
	return render(request, 'main/contact.html', {'form':form})

@login_required
def Dashboard(request):
	accounts = {}
	for currency in [ x[0] for x in CRYPTOCURRENCIES.items() ]:
		accounts[currency] = {}
		coin_accounts = request.user.crypto_accounts.filter(currency=currency)
		data = CryptoAccountSerializer(coin_accounts, many=True).data
		for datum in data:
			# id, as given in the serializer, is the CryptoAccount.eid
			accounts[currency][datum['id']] = datum
	accounts['bank'] = {}
	bank_accounts = request.user.profile.payment_network.bank_accounts
	data = BankAccountSerializer(bank_accounts, many=True).data
	for datum in data:
		accounts['bank'][datum['id']] = datum
	user = ProfileSerializer(request.user.profile).data

	recurring_orders = RecurringOrderSerializer(request.user.recurring_orders.filter(user=request.user), many=True).data

	transactions = TransactionSerializer(request.user.transactions.filter_active(user=request.user).order_by('-order__timestamp'), many=True).data

	notifications = request.user.retrieve('notifications', RetrieveUpdateNotifications.defaults)

	limits = json.dumps(request.user.get_all_limits(), cls=DjangoJSONEncoder)
	user_settings = SettingSerializer(request.user).data

	records = LoginRecordSerializer(request.user.login_records.all(), many=True).data

	return render(request, 'main/application.html', {
		'accounts':json.dumps(accounts),
		'userData':json.dumps(user),
		'notifications':json.dumps(notifications),
		'recurring_orders':json.dumps(recurring_orders, cls=DjangoJSONEncoder),
		'transactions':json.dumps(transactions, cls=DjangoJSONEncoder),
		'settings':json.dumps(user_settings, cls=DjangoJSONEncoder),
		'limits':limits,
		'fee':settings.FEE_RATIO,
		'referrer_key':request.user.referral_id,
		'referrals':request.user.referred_set.all(),
		'user':request.user,
		'login_records':json.dumps(records, cls=DjangoJSONEncoder)
	})

