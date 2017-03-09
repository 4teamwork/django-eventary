from django.shortcuts import reverse
from django.test import TestCase

from .mixins import EventTestMixin

import recurrence


class EventOrderTest(EventTestMixin, TestCase):

    # review these

    def test_sorting_management(self):
        recurring = str(recurrence.Rule(recurrence.DAILY).to_dateutil_rrule())
        events, proposals = self.create_data()
        recurring_events, recurring_proposals = self.create_data(
            recurring=recurring,
            event_length=5
        )

        self.client.login(username='manager', password='m4n4g3r')

        url = reverse('eventary:management-landing')
        response = self.client.get(url)
        self.assertEquals([
            event.recurring
            for event in response.context['proposal_list']
        ], [False] * len(proposals) + [True] * len(recurring_proposals))
        self.assertEquals([
            event.recurring
            for event in response.context['event_list']
        ], [False] * len(events) + [True] * len(recurring_events))

        self.client.logout()

    def test_sorting_editorial(self):
        recurring = str(recurrence.Rule(recurrence.DAILY).to_dateutil_rrule())
        events, proposals = self.create_data()
        recurring_events, recurring_proposals = self.create_data(
            recurring=recurring,
            event_length=5
        )

        self.client.login(username='editor', password='3d1t0r')

        url = reverse('eventary:editorial-landing')
        response = self.client.get(url)
        self.assertEquals([event.recurring
                           for event in response.context['proposal_list']],
                          [False] * len(proposals) + [True] * len(recurring_proposals))
        self.assertEquals([event.recurring
                           for event in response.context['event_list']],
                          [False] * len(events) + [True] * len(recurring_events))

        self.client.logout()

    def test_sorting_anonymous(self):
        recurring = str(recurrence.Rule(recurrence.DAILY).to_dateutil_rrule())
        events, _ = self.create_data()
        recurring_events, _ = self.create_data(
            recurring=recurring,
            event_length=5
        )

        url = reverse('eventary:anonymous-landing')
        response = self.client.get(url)
        self.assertEquals([event.recurring
                           for event in response.context['event_list']],
                          [False] * len(events) + [True] * len(recurring_events))

        url = reverse('eventary:anonymous-calendar_details',
                      kwargs={'pk': self.calendar.pk})
        response = self.client.get(url)
        self.assertEquals([event.recurring
                           for event in response.context['event_list']],
                          [False] * len(events) + [True] * len(recurring_events))
