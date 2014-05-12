from django.utils import timezone

import os
LOGGING = {
	'version' : 1,
	'disable_existing_loggers' : False,
	'handlers' : {
		'audit' : {
			'level' : 'INFO',
			# if necessary, the logging.handlers.TimedRotatingFileHandler class can also be used
			#	cf. http://bit.ly/OHBvXe
			'class' : 'logging.handlers.RotatingFileHandler',
			'filename' : os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs', 'audit.log'),
			'maxBytes' : 16 * (1024 ** 2),
		},
		'daemons' : {
			'level' : 'INFO',
			'class' : 'logging.handlers.RotatingFileHandler',
			'filename' : os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs', 'daemons.log'),
			'maxBytes' : 16 * (1024 ** 2),
		},
	},
	'loggers' : {
		'tasks.audit' : {
			'handlers' : [ 'audit', ],
			'level' : 'INFO',
		},
		'manage.daemons' : {
			'handlers' : [ 'daemons', ],
			'level' : 'INFO',
		},
		'tasks.daemons' : {
			'handlers' : [ 'daemons', ],
			'level' : 'INFO',
		},
	},
}

def log(logger, msg):
	message = '%s\t%s' % ( str(timezone.now()), str(msg), )
	logger.info(message)
