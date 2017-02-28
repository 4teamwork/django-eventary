from datetime import datetime

from django.shortcuts import reverse
from django.test import Client, TestCase
from django.urls.exceptions import NoReverseMatch

from .. import urls
from ..models import Calendar, Event, EventTimeDate, Secret


class AnonymousUserAccess(TestCase):

    def setUp(self):
        self.client = Client()
        self.calendar = Calendar.objects.create(
            title='TestCalendar',
            view_limit=1,
        )
        self.event = Event.objects.create(
            calendar=self.calendar,
            title='Event',
            host='TestHost',
            published=True,
        )
        self.proposal = Event.objects.create(
            calendar=self.calendar,
            title='Proposal',
            host='TestHost',
            published=False,
        )
        self.eventtimedate = EventTimeDate.objects.create(
            event=self.event,
            start_date=datetime.today(),
        )
        self.proposaltimedate = EventTimeDate.objects.create(
            event=self.proposal,
            start_date=datetime.today()
        )
        self.secret = Secret.objects.create(
            event=self.proposal
        )

    def test_redirect_when_no_access(self):

        # some url patterns require arguments, these patterns are stored in
        # `to_test`
        to_test = []

        for urlpattern in urls.urlpatterns:

            if not urlpattern.name.startswith('anonymous'):
                try:
                    url = reverse('eventary:{0}'.format(urlpattern.name))
                    response = self.client.get(url)

                    # assert a redirection
                    self.assertEqual(response.status_code, 302)

                except NoReverseMatch:
                    to_test.append(urlpattern.name)

        # the special cases need arguments
        special_cases = {
            'editorial-delete_event': {'pk': self.event.pk,
                                       'calendar_pk': self.calendar.pk},
            'editorial-list_proposals': {'pk': self.calendar.pk},
            'editorial-publish_event': {'pk': self.proposal.pk,
                                        'calendar_pk': self.calendar.pk},
            'editorial-update_event': {'pk': self.calendar.pk,
                                       'event_pk': self.event.pk},
            'management-delete_calendar': {'pk': self.calendar.pk},
            'management-update_calendar': {'pk': self.calendar.pk},
        }

        # assert all special cases are dealt
        self.assertEquals(sorted(to_test), sorted(special_cases.keys()))

        # deal all the special cases
        for name, kwargs in special_cases.items():

            # assume status 302 unless a status is given in the kwargs
            status = kwargs.pop('status', 302)

            # assert the status codes
            url = reverse('eventary:{0}'.format(name), kwargs=kwargs)
            response = self.client.get(url)
            self.assertEquals(response.status_code, status)

    def test_access(self):

        # some url patterns require arguments, these patterns are stored in
        # `to_test`
        to_test = []

        for urlpattern in urls.urlpatterns:

            if (
                not urlpattern.name.startswith('management') and
                not urlpattern.name.startswith('editorial') and
                not urlpattern.name.startswith('redirector')
            ):
                try:
                    url = reverse('eventary:{0}'.format(urlpattern.name))
                    response = self.client.get(url)

                    # assert a valid 200 status code
                    self.assertEqual(response.status_code,
                                     200,
                                     urlpattern.name)

                except NoReverseMatch:
                    to_test.append(urlpattern.name)

        # the special cases need arguments
        special_cases = {
            'anonymous-calendar_details': {'pk': self.calendar.pk},
            'anonymous-create_event': {'pk': self.calendar.pk},
            'anonymous-event_details': {
                'calendar_pk': self.calendar.pk,
                'pk': self.event.pk
            },
            'anonymous-export_event_to_ics': {
                'calendar_pk': self.calendar.pk,
                'pk': self.event.pk
            },
            'anonymous-proposal_details': {
                'calendar_pk': self.calendar.pk,
                'pk': self.proposal.pk,
                'secret': str(self.secret.secret)
            },
        }

        # assert all special cases are dealt
        self.assertEquals(sorted(to_test), sorted(special_cases.keys()))

        # deal all the special cases
        for name, kwargs in special_cases.items():

            # assume status 200 unless a status is given in the kwargs
            status = kwargs.pop('status', 200)

            # assert the status codes
            url = reverse('eventary:{0}'.format(name), kwargs=kwargs)
            response = self.client.get(url)

            self.assertEquals(response.status_code, status)
