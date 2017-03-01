from datetime import datetime
from datetime import timedelta as td

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.shortcuts import reverse
from django.test import Client, TestCase

from ..models import Calendar, Event, EventTimeDate, Secret


class EventFilterTest(TestCase):

    def setUp(self):

        self.today = datetime.today().date()
        self.now = datetime.now()

        self.client = Client()

        self.manager = User.objects.create(
            username='manager',
            password=make_password('m4n4g3r')
        )
        management = Group.objects.get(name='eventary_management')
        self.manager.groups.add(management)

        self.editor = User.objects.create(
            username='editor',
            password=make_password('3d1t0r')
        )
        editorial = Group.objects.get(name='eventary_editorial')
        self.editor.groups.add(editorial)

        self.calendar = Calendar.objects.create(
            title='TestCalendar',
            view_limit=1
        )

    def create_data(self, nr_events=5, event_length=None, recurring=False):
        # create published events
        events = [Event.objects.create(
            calendar=self.calendar,
            title='{0} Event'.format(i),
            host='TestHost',
            location='TestLocation',
            published=True,
            recurring=recurring,
        ) for i in range(nr_events)]

        # create the timedates for the events
        if event_length is not None:
            [EventTimeDate.objects.create(
                event=events[i],
                start_date=self.today + td(days=i),
                end_date=self.today + td(days=i + event_length)
            ) for i in range(nr_events)]
        else:
            [EventTimeDate.objects.create(
                event=events[i],
                start_date=self.today + td(days=i)
            ) for i in range(nr_events)]

        # create the proposed events
        proposals = [Event.objects.create(
            calendar=self.calendar,
            title='{0} Proposal'.format(i),
            host='TestHost',
            location='TestLocation',
            published=False,
            recurring=recurring,
        ) for i in range(nr_events)]

        # create the secrets for the proposals
        [Secret.objects.create(event=proposals[i]) for i in range(nr_events)]

        # create the timedates for the proposals
        if event_length is not None:
            [EventTimeDate.objects.create(
                event=proposals[i],
                start_date=self.today + td(days=i),
                end_date=self.today + td(days=i + event_length)
            ) for i in range(nr_events)]
        else:
            [EventTimeDate.objects.create(
                event=proposals[i],
                start_date=self.today + td(days=i)
            ) for i in range(nr_events)]

        return events, proposals

    def single_filter_data(self, nr_events=5):
        """Returns the request data for the expected number of count events"""

        # if we have n events, we want to generate data to test filtering of
        #     0, 1, ..., n events
        # setting
        #     `from_date` and `to_date`
        #     `from_date` only
        #     `to_date` only
        return {
            (nr_events - counter): {
                'from & to': [
                    {'filter-from_date': (
                        self.today + td(days=i)
                     ).strftime('%Y-%m-%d'),
                     'filter-to_date': (
                        self.today + td(days=i + (nr_events - counter) - 1)
                     ).strftime('%Y-%m-%d')}
                    for i in range(counter + 1)
                ],
                'from only': [{'filter-from_date': (
                    self.today + td(days=counter)
                ).strftime('%Y-%m-%d')}],
                'to only': [{'filter-to_date': (
                    self.today + td(days=nr_events - 1 - counter)
                ).strftime('%Y-%m-%d')}]
            }
            for counter in range(nr_events+1)
        }

    def multiple_filter_data(self, event_length=2, nr_events=5):
        """Returns the request data for the expected number of count events"""

        # if we have n events, we want to generate data to test filtering of
        #     0, 1, ..., n events
        # setting
        #     `from_date` and `to_date`
        #     `from_date` only
        #     `to_date` only
        return {
            (nr_events - counter): {
                'from & to': [
                    {'filter-from_date': (
                        self.today + td(days=counter - i)
                    ).strftime('%Y-%m-%d'),
                     'filter-to_date': (
                        self.today + td(days=nr_events - 1 - i + event_length)
                    ).strftime('%Y-%m-%d')}
                    for i in range(counter + 1)
                ],
                'from only': [{'filter-from_date': (
                    self.today + td(days=counter)
                ).strftime('%Y-%m-%d')}],
                'to only': [{'filter-to_date': (
                    self.today + td(
                        days=nr_events - 1 - counter + event_length
                    )
                ).strftime('%Y-%m-%d')}],
            }
            for counter in range(nr_events)
        }

    def _test_filter_run(self, events, proposals, data):

        # AS MANAGEMENT
        self.client.login(username='manager', password='m4n4g3r')
        url = reverse('eventary:management-landing')

        # go through all the possible filters
        for count, labeled_filters in data.items():
            for message, parameters_list in labeled_filters.items():
                for filter_parameters in parameters_list:
                    response = self.client.get(url, filter_parameters)
                    self.assertEquals(
                        response.context['event_list'].count(),
                        count,
                        message
                    )
                    self.assertEquals(
                        response.context['proposal_list'].count(),
                        count,
                        message
                    )

        self.client.logout()

        # AS EDITORIAL
        self.client.login(username='editor', password='3d1t0r')
        url = reverse('eventary:editorial-landing')

        # go through all the possible filters
        for count, labeled_filters in data.items():
            for message, parameters_list in labeled_filters.items():
                for filter_parameters in parameters_list:
                    response = self.client.get(url, filter_parameters)
                    self.assertEquals(
                        response.context['event_list'].count(),
                        count,
                        message
                    )
                    self.assertEquals(
                        response.context['proposal_list'].count(),
                        count,
                        message
                    )

        self.client.logout()

        # AS ANONYMOUS
        url = reverse('eventary:anonymous-landing')

        # go through all the possible filters
        for count, labeled_filters in data.items():
            for message, parameters_list in labeled_filters.items():
                for filter_parameters in parameters_list:
                    response = self.client.get(url, filter_parameters)
                    self.assertEquals(
                        response.context['event_list'].count(),
                        count,
                        message
                    )

        url = reverse('eventary:anonymous-calendar_details',
                      kwargs={'pk': self.calendar.pk})

        # go through all the possible filters
        for count, labeled_filters in data.items():
            for message, parameters_list in labeled_filters.items():
                for filter_parameters in parameters_list:
                    response = self.client.get(url, filter_parameters)
                    self.assertEquals(
                        response.context['event_list'].count(),
                        count,
                        message
                    )

    def test_single_day_event_filters(self):
        events, proposals = self.create_data()
        self._test_filter_run(events, proposals, self.single_filter_data())

    def test_multiple_day_event_filters(self):
        events, proposals = self.create_data(event_length=2)
        self._test_filter_run(events,
                              proposals,
                              self.multiple_filter_data(event_length=2))
