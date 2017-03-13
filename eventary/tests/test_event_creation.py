import os

from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import reverse
from django.test import Client, TestCase

from ..models import Calendar


class EventCreation(TestCase):

    def setUp(self):
        self.client = Client()
        self.calendar = Calendar.objects.create(
            title='TestCalendar',
            view_limit=1,
        )
        self.url = reverse('eventary:anonymous-create_event',
                           kwargs={'pk': self.calendar.pk})

    def test_event_creation(self):
        response = self.client.post(self.url, {
            'event_create_wizard_view-current_step': '0',
            '0-name': 'TestVerunstalter',
            '0-info': '',
            '0-phone': '0797792750',
            '0-email': '',
            '0-homepage': ''
        })

        self.assertEquals(
            200,
            response.status_code,
            'wrong status code when posting host'
        )

        TEST_DIR = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(TEST_DIR, 'logo-superman.png')) as image:
            response = self.client.post(self.url, {
                'event_create_wizard_view-current_step': '1',
                '1-title': 'TestVerunstaltung',
                '1-location': 'TestVerunstaltungsort',
                '1-image': '',
                '1-document': '',
                '1-homepage': '',
                '1-description': '',
                '1-comment': '',
                '1-prize': '',
                '1-recurring': False,
                # TODO: add 'grouping-grouping.title': (group1.pk, group2.pk)
            })

            self.assertEquals(
                200,
                response.status_code,
                'wrong status code when posting event data'
            )

        response = self.client.post(self.url, {
            'event_create_wizard_view-current_step': '2',
            '2-start_date': '01.01.2017',
            '2-start_time': '19:30',
            '2-end_date': '31.12.2017',
            '2-end_time': '22:30',
            'recurrence-recurrences': "\n".join([
                'RRULE:FREQ=WEEKLY;BYDAY=MO,WE,SA',
                'EXRULE:FREQ=MONTHLY;BYDAY=-1SA'
            ])
        })

        self.assertEquals(
            302,
            response.status_code,
            'wrong status code when posting date data'
        )
