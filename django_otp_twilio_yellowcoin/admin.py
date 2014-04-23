from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

from .models import TwilioSMSDevice


class TwilioSMSDeviceAdmin(admin.ModelAdmin):
    """
    :class:`~django.contrib.admin.ModelAdmin` for
    :class:`~django_otp_twilio_yellowcoin.models.TwilioSMSDevice`.
    """
    fieldsets = [
        ('Identity', {
            'fields': ['user', 'name', 'confirmed'],
        }),
        ('Configuration', {
            'fields': ['number', 'key'],
        }),
    ]


try:
    admin.site.register(TwilioSMSDevice, TwilioSMSDeviceAdmin)
except AlreadyRegistered:
    # Ignore the useless exception from multiple imports
    pass
