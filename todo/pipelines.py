from datetime import datetime
from google.appengine.api import app_identity
from google.appengine.api import taskqueue
from mapreduce import base_handler
from mapreduce import mapreduce_pipeline
from todo.blueprints import app_user
from todo.models.calendar import Calendar
from todo.models.event import Event


class ExportPipeline(base_handler.PipelineBase):

    def run(self, *args, **kwargs):
        params = {
            'entity_kind': 'todo.models.user.User',
            'output_writer': {
                'bucket_name': app_identity.get_default_gcs_bucket_name(),
                'content_type': 'text/plain',
            },
        }
        yield mapreduce_pipeline.MapperPipeline(
            'export',
            'todo.pipelines.ExportPipeline.map',
            'mapreduce.input_readers.DatastoreInputReader',
            'mapreduce.output_writers.GoogleCloudStorageConsistentOutputWriter',
            params=params)

    @staticmethod
    def map(user):
        tag = '"%s"' % user.get_hash()
        days = (datetime.now() - user.created).days

        calendars = 0
        todos = 0
        completed = 0
        for calendar in Calendar.get_all(user.key):
            calendars += 1
            for event in Event.get_all(calendar.key):
                todos += 1
                if event.done:
                    completed += 1

        row = (tag, days, calendars, todos, completed)
        row = [str(col) for col in row]
        yield (','.join(row) + '\n')

class SyncPipeline(base_handler.PipelineBase):

    def run(self, *args, **kwargs):
        params = {
            'entity_kind': 'todo.models.user.User',
        }
        yield mapreduce_pipeline.MapperPipeline(
            'sync',
            'todo.pipelines.SyncPipeline.map',
            'mapreduce.input_readers.DatastoreInputReader',
            params=params)

    @staticmethod
    def map(user):
        task_url = '/api/v1/queues/sync/user'
        params = {
            'user_id': user.key.urlsafe()
        }

        try:
            if user.synced is not None:
                taskqueue.add(url=task_url, params=params)
        except AttributeError:
            pass

class IndexPipeline():

    @staticmethod
    def map(user):
        user.index()

