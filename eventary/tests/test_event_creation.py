from datetime import datetime, timedelta

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

    # tests with invalid timedate form
    def _timedateform_invalid_assertions(self, response):
        self.assertNotEquals(
            response.status_code,
            302,
            'unexpected redirection (ergo, the event was created)'
        )
        self.assertEquals(
            response.status_code,
            200,
            'expected a status 200 (ergo displaying the form view again)'
        )
        self.assertTrue(response.context['eventform'].is_valid(),
                        'expected valid event data form')
        self.assertFalse(response.context['timedateform'].is_valid(),
                         'expected invalid time date form')
        self.assertTrue(response.context['groupingform'].is_valid(),
                        'expected valid event grouping form')

    def test_end_time_but_no_start_time_given(self):
        response = self.client.post(self.url, {
            'title': 'TestEvent',
            'host': 'TestHost',
            'start_date': datetime.today().strftime('%Y-%m-%d'),
            'end_time': '12:00'
        })
        self._timedateform_invalid_assertions(response)

    def test_no_start_date_given(self):
        response = self.client.post(self.url, {
            'title': 'TestEvent',
            'host': 'TestHost',
        })
        self._timedateform_invalid_assertions(response)

    def test_start_date_after_end_date(self):
        response = self.client.post(self.url, {
            'title': 'TestEvent',
            'host': 'TestHost',
            'start_date': (datetime.today() + timedelta(days=1)).strftime(
                '%Y-%m-%d'
            ),
            'end_date': datetime.today().strftime('%Y-%m-%d'),
        })
        self._timedateform_invalid_assertions(response)

    # tests with invalid event data form
    def _eventform_invalid_assertions(self, response):
        self.assertNotEquals(
            response.status_code,
            302,
            'unexpected redirection (ergo, the event was created)'
        )
        self.assertEquals(
            response.status_code,
            200,
            'expected a status 200 (ergo displaying the form view again)'
        )
        self.assertFalse(response.context['eventform'].is_valid(),
                         'expected valid event data form')
        self.assertTrue(response.context['timedateform'].is_valid(),
                        'expected invalid time date form')
        self.assertTrue(response.context['groupingform'].is_valid(),
                        'expected valid event grouping form')

    def test_no_event_title(self):
        response = self.client.post(self.url, {
            'host': 'TestHost',
            'start_date': datetime.today().strftime('%Y-%m-%d'),
        })
        self._eventform_invalid_assertions(response)
