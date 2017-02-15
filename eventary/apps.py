from django.apps import AppConfig


class EventaryConfig(AppConfig):
    name = 'eventary'

    def ready(self):
        from eventary import signals  # noqa
