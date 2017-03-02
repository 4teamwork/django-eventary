from django.shortcuts import reverse
from django.test import TestCase

from .mixins import EventTestMixin


class EventOrderTest(EventTestMixin, TestCase):

    def test_sorting_management(self):
        events, proposals = self.create_data()
        recurring_events, recurring_proposals = self.create_data(
            recurring=True,
            event_length=5
        )

        self.client.login(username='manager', password='m4n4g3r')

        url = reverse('eventary:management-landing')
        response = self.client.get(url)
        self.assertEquals([event.recurring
                           for event in response.context['proposal_list']],
                          [False] * len(proposals) + [True] * len(recurring_proposals))
        self.assertEquals([event.recurring
                           for event in response.context['event_list']],
                          [False] * len(events) + [True] * len(recurring_events))

        self.client.logout()

    def test_sorting_editorial(self):

        events, proposals = self.create_data()
        recurring_events, recurring_proposals = self.create_data(
            recurring=True,
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
        
        events, _ = self.create_data()
        recurring_events, _ = self.create_data(
            recurring=True,
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
