from datetime import timedelta as td

from django.shortcuts import reverse
from django.test import TestCase

from .mixins import EventTestMixin


class EventFilterTest(EventTestMixin, TestCase):

    def single_filter_data(self, nr_events=5):
        """Returns the request data for the expected number of count events"""

        # if we have n events, we want to generate data to test filtering of
        #     0, 1, ..., n events
        # setting
        #     `from_date` and `to_date`
        #     `from_date` only
        #     `to_date` only
        to_return = {
            0: {'from & to': [{
                    'filter-from_date': (self.today - td(days=2)).strftime(
                        '%Y-%m-%d'
                    ),
                    'filter-to_date': (self.today - td(days=1)).strftime(
                        '%Y-%m-%d'
                    ),
                }],
                'from only': [{
                    'filter-from_date': (self.today + td(days=6)).strftime(
                        '%Y-%m-%d'
                    ),
                }],
                'to only': [{
                    'filter-to_date': (self.today - td(days=1)).strftime(
                        '%Y-%m-%d'
                    ),
                }]}
        }
        to_return.update({
            (nr_events - counter): {
                'from & to': [
                    {'filter-from_date': (
                        self.today + td(days=i)
                     ).strftime('%Y-%m-%d'),
                     'filter-to_date': (
                        self.today + td(days=i + (nr_events - counter) - 1)
                     ).strftime('%Y-%m-%d')}
                    for i in range(counter)
                ],
                'from only': [{'filter-from_date': (
                    self.today + td(days=counter)
                ).strftime('%Y-%m-%d')}],
                'to only': [{'filter-to_date': (
                    self.today + td(days=nr_events - 1 - counter)
                ).strftime('%Y-%m-%d')}]
            }
            for counter in range(nr_events)
        })
        return to_return

    def multiple_filter_data(self, event_length=2, nr_events=5):
        """Returns the request data for the expected number of count events"""

        # if we have n events, we want to generate data to test filtering of
        #     0, 1, ..., n events
        # setting
        #     `from_date` and `to_date`
        #     `from_date` only
        #     `to_date` only
        return {(nr_events - c): {
            'from & to': [
                {'filter-from_date': (
                    self.today + td(days=c - i)
                ).strftime('%Y-%m-%d'),
                 'filter-to_date': (
                    self.today + td(days=nr_events - 1 - i + event_length)
                ).strftime('%Y-%m-%d')}
                for i in range(c + 1)
            ],
            'from only': [{
                'filter-from_date': (
                    self.today + td(days=c)
                ).strftime('%Y-%m-%d')
            }],
            'to only': [{
                'filter-to_date': (
                    self.today + td(days=nr_events - 1 - c + event_length)
                 ).strftime('%Y-%m-%d')
            }],
        } for c in range(nr_events)}

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
                        '{2} expected {0} events, filters {1}'.format(
                            count,
                            message,
                            'management'
                        )
                    )
                    self.assertEquals(
                        response.context['proposal_list'].count(),
                        count,
                        '{2} expected {0} proposals, filters {1}'.format(
                            count,
                            message,
                            'management'
                        )
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
