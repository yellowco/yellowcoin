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
	},
	'loggers' : {
		'tasks.audit' : {
			'handlers' : [ 'audit', ],
			'level' : 'INFO',
		},
	},
}
