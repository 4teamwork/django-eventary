import requests

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError

from ...models import Calendar, Event, EventHost, EventTimeDate

URL = 'https://www.googleapis.com/calendar/v3/calendars/{gcal_id}/events'


def _datetime_to_gdatetime(dt):
    to_return = dt.strftime('%Y-%m-%dT%H:%M:%S%z')
    if '+' not in to_return:
        to_return += '+0000'
    return to_return


class Command(BaseCommand):
    help = 'Imports the specified google calendar'

    def add_arguments(self, parser):
        today = datetime.today()
        today_in_a_week = today + timedelta(days=7)
        parser.add_argument('google_calendar_id', nargs='+', type=str)
        parser.add_argument('calendar_id', nargs=1, type=int)
        parser.add_argument('time_min',
                            default=_datetime_to_gdatetime(today),
                            nargs='?',
                            type=str)
        parser.add_argument('time_max',
                            default=_datetime_to_gdatetime(today_in_a_week),
                            nargs='?',
                            type=str)

    def handle_calendar(self, gcal_id):
        request = requests.get(
            URL.format(gcal_id=gcal_id),
            params={
                'key': 'AIzaSyBNlYH01_9Hc5S1J9vuFmu2nUqBZJNAXxs',
                'singleEvents': True,
                'timeZone': 'Europe/Zurich',
                'maxResults': 250,
                'timeMin': self.options.get('time_min'),
                'timeMax': self.options.get('time_max'),
            }
        )
        if request.status_code is 200:
            json = request.json()
            for event_data in json['items']:
                # use iCalUID to check if the event was imported already
                # todo: icaluid = event_data['iCalUID']
                self.handle_event_data(event_data)
        else:
            raise CommandError(
                'Import failed, request status code {status_code}'.format(
                    status_code=request.status_code
                )
            )
        self.stdout.write(self.style.SUCCESS(
            'Successfully imported calendar "{gcal_id}"'.format(
                gcal_id=gcal_id
            )
        ))

    def handle_event_data(self, event_data):

        # get or create the host
        host_data = event_data['organizer']
        host, created = EventHost.objects.get_or_create(
            name='DWS Google Calendar',
            info='DWS Google Calendar',
            phone='DWS Google Calendar',
            email=host_data['email'],
            notify=False,
        )

        # get or create the event
        event, created = Event.objects.get_or_create(
            calendar=self.calendar,
            title=event_data['summary'],
            host=host,
            location=event_data.get('location', 'DWS Google Calendar'),
            homepage=event_data.get('htmlLink'),
            published=True,
            description=event_data.get('description'),
            recurring='recurringEventId' in event_data,
        )

        # get or create the date and times
        kwargs = {}
        kwargs.update(self.handle_datetime_data(event_data['start'],
                                                prefix='start'))
        kwargs.update(self.handle_datetime_data(event_data['end'],
                                                prefix='end'))

        timedate, created = EventTimeDate.objects.get_or_create(
            event=event,
            **kwargs
        )

        self.stdout.write(self.style.SUCCESS(
            'Successfully imported event into calendar "{calendar}"'.format(
                calendar=self.calendar.title,
            )
        ))

    def handle_datetime_data(self, datetime_data, prefix):
        if 'dateTime' in datetime_data:
            first, second = datetime_data.get('dateTime').split('+')
            dt = datetime.strptime(
                '{first}+{second}'.format(
                    first=first,
                    second=second.replace(':', '') or '0000'
                ),
                '%Y-%m-%dT%H:%M:%S%z'
            )
            return {
                '{prefix}_date'.format(prefix=prefix): dt.date(),
                '{prefix}_time'.format(prefix=prefix): dt.time(),
            }
        else:
            dt = datetime.strptime(datetime_data.get('date'),
                                   '%Y-%m-%d')
            return {'{prefix}_date'.format(prefix=prefix): dt.date()}

    def handle(self, *args, **options):
        try:
            calendar_pk = options.get('calendar_id')[0]
            self.calendar = Calendar.objects.get(pk=calendar_pk)
        except Calendar.DoesNotExist:
            raise CommandError(
                'Import failed, calendar with pk "{pk}" not found'.format(
                    pk=calendar_pk
                )
            )
        self.options = options
        for gcal_id in options['google_calendar_id']:
            self.handle_calendar(gcal_id)
