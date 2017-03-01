from datetime import datetime
from datetime import timedelta as td

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.shortcuts import reverse
from django.test import Client, TestCase

from ..models import Calendar, Event, EventTimeDate, Secret


class FilterTest(TestCase):

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

    def single_filter_data(self, max_counter=5):
        """Returns the request data for the expected number of count events"""

        # ay-yeah! list comprehension in a dict comprehension
        return {
            (max_counter - counter): [
                ({'filter-from_date': (
                    self.today + td(days=i)
                  ).strftime('%Y-%m-%d'),
                  'filter-to_date': (
                    self.today + td(days=i + (max_counter - counter) - 1)
                  ).strftime('%Y-%m-%d')}, 'from & to')
                for i in range(counter + 1)
            ] + [
                ({'filter-from_date': (self.today + td(days=counter)).strftime(
                    '%Y-%m-%d'
                )}, 'from only'),
                ({'filter-to_date': (
                    self.today + td(days=max_counter - 1 - counter)
                ).strftime('%Y-%m-%d')}, 'to only')
            ] for counter in range(max_counter+1)
        }

    def test_single_day_event_filters(self):

        # create published events
        events = [Event.objects.create(
            calendar=self.calendar,
            title='{0} Event'.format(i),
            host='TestHost',
            location='TestLocation',
            published=True,
        ) for i in range(5)]

        # create the timedates for the events
        [EventTimeDate.objects.create(
            event=events[i],
            start_date=self.today + td(days=i)
        ) for i in range(5)]

        # create the proposed events
        proposals = [Event.objects.create(
            calendar=self.calendar,
            title='{0} Proposal'.format(i),
            host='TestHost',
            location='TestLocation',
            published=False,
        ) for i in range(5)]

        # create the secrets for the proposals
        [Secret.objects.create(event=proposals[i]) for i in range(5)]

        # create the timedates for the proposals
        [EventTimeDate.objects.create(
            event=proposals[i],
            start_date=self.today + td(days=i)
        ) for i in range(5)]

        # AS MANAGEMENT
        self.client.login(username='manager', password='m4n4g3r')
        url = reverse('eventary:management-landing')

        # go through all the possible filters
        for count, parameters_list in self.single_filter_data().items():
            for filter_parameters, message in parameters_list:
                response = self.client.get(url, filter_parameters)
                self.assertEquals(response.context['event_list'].count(),
                                  count,
                                  message)
                self.assertEquals(response.context['proposal_list'].count(),
                                  count,
                                  message)

        self.client.logout()

        # AS EDITORIAL
        self.client.login(username='editor', password='3d1t0r')
        url = reverse('eventary:editorial-landing')

        # go through all the possible filters
        for count, parameters_list in self.single_filter_data().items():
            for filter_parameters, message in parameters_list:
                response = self.client.get(url, filter_parameters)
                self.assertEquals(response.context['event_list'].count(),
                                  count,
                                  message)
                self.assertEquals(response.context['proposal_list'].count(),
                                  count,
                                  message)

        self.client.logout()

        # AS ANONYMOUS
        url = reverse('eventary:anonymous-landing')

        # go through all the possible filters
        for count, parameters_list in self.single_filter_data().items():
            for filter_parameters, message in parameters_list:
                response = self.client.get(url, filter_parameters)
                self.assertEquals(response.context['event_list'].count(),
                                  count,
                                  message)
        response = self.client.get(url)

        url = reverse('eventary:anonymous-calendar_details',
                      kwargs={'pk': self.calendar.pk})

        # go through all the possible filters
        for count, parameters_list in self.single_filter_data().items():
            for filter_parameters, message in parameters_list:
                response = self.client.get(url, filter_parameters)
                self.assertEquals(response.context['event_list'].count(),
                                  count,
                                  message)

    def multiple_filter_data(self, max_counter=5):
        """Returns the request data for the expected number of count events"""

        # ay-yeah! list comprehension in a dict comprehension
        return {
            (max_counter - counter): [
                ({'filter-from_date': (
                    self.today + td(days=counter - number)
                  ).strftime('%Y-%m-%d'),
                  'filter-to_date': (
                    self.today + td(days=max_counter - 1 - number + 2)
                  ).strftime('%Y-%m-%d')}, 'from & to')
                for number in range(1 + counter)
            ] + [
                ({'filter-from_date': (self.today + td(days=counter)).strftime(
                    '%Y-%m-%d'
                )}, 'from only'),
                ({'filter-to_date': (
                    self.today + td(days=max_counter - 1 - counter + 2)
                ).strftime('%Y-%m-%d')}, 'to only')
            ]
            for counter in range(max_counter)
        }

    def test_multiple_day_event_filters(self):

        # create published events
        events = [Event.objects.create(
            calendar=self.calendar,
            title='{0} Event'.format(i),
            host='TestHost',
            location='TestLocation',
            published=True,
        ) for i in range(5)]

        # create the timedates for the events
        [EventTimeDate.objects.create(
            event=events[i],
            start_date=self.today + td(days=i),
            end_date=self.today + td(days=i + 2)
        ) for i in range(5)]

        # create the proposed events
        proposals = [Event.objects.create(
            calendar=self.calendar,
            title='{0} Proposal'.format(i),
            host='TestHost',
            location='TestLocation',
            published=False,
        ) for i in range(5)]

        # create the secrets for the proposals
        [Secret.objects.create(event=proposals[i]) for i in range(5)]

        # create the timedates for the proposals
        [EventTimeDate.objects.create(
            event=proposals[i],
            start_date=self.today + td(days=i),
            end_date=self.today + td(days=i + 2)
        ) for i in range(5)]

        # AS MANAGEMENT
        self.client.login(username='manager', password='m4n4g3r')
        url = reverse('eventary:management-landing')

        # go through all the possible filters
        for count, parameters_list in self.multiple_filter_data().items():
            for filter_parameters, message in parameters_list:
                response = self.client.get(url, filter_parameters)
                self.assertEquals(response.context['event_list'].count(),
                                  count,
                                  message)
                self.assertEquals(response.context['proposal_list'].count(),
                                  count,
                                  message)

        self.client.logout()

        # AS EDITORIAL
        self.client.login(username='editor', password='3d1t0r')
        url = reverse('eventary:editorial-landing')

        # go through all the possible filters
        for count, parameters_list in self.multiple_filter_data().items():
            for filter_parameters, message in parameters_list:
                response = self.client.get(url, filter_parameters)
                self.assertEquals(response.context['event_list'].count(),
                                  count,
                                  message)
                self.assertEquals(response.context['proposal_list'].count(),
                                  count,
                                  message)

        self.client.logout()

        # AS ANONYMOUS
        url = reverse('eventary:anonymous-landing')

        # go through all the possible filters
        for count, parameters_list in self.multiple_filter_data().items():
            for filter_parameters, message in parameters_list:
                response = self.client.get(url, filter_parameters)
                self.assertEquals(response.context['event_list'].count(),
                                  count,
                                  message)
        response = self.client.get(url)

        url = reverse('eventary:anonymous-calendar_details',
                      kwargs={'pk': self.calendar.pk})

        # go through all the possible filters
        for count, parameters_list in self.multiple_filter_data().items():
            for filter_parameters, message in parameters_list:
                response = self.client.get(url, filter_parameters)
                self.assertEquals(response.context['event_list'].count(),
                                  count,
                                  message)
