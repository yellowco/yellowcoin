CELERY_IMPORTS = ('yellowcoin.transactions.tasks',)
CELERY_ACCEPT_CONTENT = ['pickle', 'json']
BROKER_URL = 'redis://localhost:6379/0'
