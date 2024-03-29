import django.conf

from django.utils.six import iteritems


class Settings(object):
    """
    This is a simple class to take the place of the global settings object. An
    instance will contain all of our settings as attributes, with default values
    if they are not specified by the configuration.
    """
    defaults = {
        'OTP_TWILIO_ACCOUNT': None,
        'OTP_TWILIO_AUTH': None,
        'OTP_TWILIO_FROM': None,
        'OTP_TWILIO_NO_DELIVERY': False,
		'OTP_TWILIO_RATE_LIMIT_INTERVAL': 30
    }

    def __init__(self):
        """
        Loads our settings from django.conf.settings, applying defaults for any
        that are omitted.
        """
        for name, default in iteritems(self.defaults):
            value = getattr(django.conf.settings, name, default)
            setattr(self, name, value)


settings = Settings()
