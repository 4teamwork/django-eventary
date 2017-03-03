from datetime import datetime

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

    def test_end_time_but_no_start_time_given(self):
        # create an event
        url = reverse('eventary:anonymous-create_event',
                      kwargs={'pk': self.calendar.pk})
        response = self.client.post(url, {
            'title': 'TestEvent',
            'host': 'TestHost',
            'start_date': datetime.today().strftime('%Y-%m-%d')
        })
        import pdb; pdb.set_trace()
