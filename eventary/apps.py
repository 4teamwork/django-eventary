from django.apps import AppConfig


class EventaryConfig(AppConfig):
    name = 'eventary'

    def ready(self):
        from . import signals, specs  # noqa
