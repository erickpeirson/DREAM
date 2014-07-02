## Broker settings.
BROKER_URL = 'amqp://dream:dreamer@localhost:5672/dreamhost'
CELERY_RESULT_BACKEND = "amqp"

CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_CHORD_PROPAGATES = True
#CELERY_TASK_SERIALIZER = "json"
#CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']

## List of modules to import when celery starts.
#CELERY_IMPORTS = ('myapp.tasks', )

## Using the database to store task state and results.
#CELERY_RESULT_BACKEND = 'db+sqlite:///results.db'

#CELERY_ANNOTATIONS = {'tasks.add': {'rate_limit': '10/s'}}