from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.shortcuts import reverse
from django.test import Client, TestCase

from ..models import Calendar, Event


class BusinessLogicTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.editor = User.objects.create(
            username='editor',
            password=make_password('3d1t0r')
        )
        editorial = Group.objects.get(name='eventary_editorial')
        self.editor.groups.add(editorial)

        self.manager = User.objects.create(
            username='manager',
            password=make_password('m4n4g3r')
        )
        management = Group.objects.get(name='eventary_management')
        self.manager.groups.add(management)

    def test_business_logic(self):

        #  AS MANAGEMENT
        self.client.login(username='manager', password='m4n4g3r')

        # create a calendar
        url = reverse('eventary:management-create_calendar')
        response = self.client.post(url, {
            'title': 'TestCalendarrr',
            'view_limit': 2
        })
        calendar = Calendar.objects.get(title='TestCalendarrr')

        # update a calendar
        url = reverse('eventary:management-update_calendar',
                      kwargs={'pk': calendar.pk})
        response = self.client.post(url, {
            'title': 'TestCalendar',
            'view_limit': 1
        })
        calendar = Calendar.objects.get(title='TestCalendar')
        with self.assertRaises(Calendar.DoesNotExist):
            Calendar.objects.get(title='TestCalendarrr')
        self.assertEquals(calendar.view_limit, 1, 'calendar view limit')

        # delete a calendar
        url = reverse('eventary:management-delete_calendar',
                      kwargs={'pk': calendar.pk})
        response = self.client.get(url)
        self.assertTrue('csrf_token' in response.context, 'no csrf token')
        response = self.client.post(url, {
            'csrf_token': response.context['csrf_token'].format()
        })
        with self.assertRaises(Calendar.DoesNotExist):
            Calendar.objects.get(pk=calendar.pk)

        # create a new calendar
        url = reverse('eventary:management-create_calendar')
        response = self.client.post(url, {
            'title': 'TestCalendar',
            'view_limit': 1
        })
        calendar = Calendar.objects.get(title='TestCalendar')

        #  AS ANONYMOUS
        self.client.logout()

        return
        # TODO: continue from here -> fix the creation of event

        # create a "bad" and a "good" event
        url = reverse('eventary:anonymous-create_event',
                      kwargs={'pk': calendar.pk})
        response = self.client.post(url, {
            'name': 'HostName',
            'phone': 'some phone number',
            'title': 'BadTestEvent',
            'start_date': datetime.today().strftime('%Y-%m-%d'),
        })
        # if creation was successful, then we get a redirection and the
        self.assertEquals(response.status_code, 302)
        response = self.client.post(url, {
            'name': 'HostName',
            'phone': 'some phone number',
            'title': 'GoodTestEvent',
            'start_date': datetime.today().strftime('%Y-%m-%d'),
        })
        # if creation was successful, then we get a redirection and the
        self.assertEquals(response.status_code, 302)
        bad, good = list(Event.objects.filter(title__in=['BadTestEvent',
                                                         'GoodTestEvent']))

        # response object has an url with the secret
        self.assertTrue(getattr(response, 'url', False))

        # now access the event with the given secret url
        secret_url = response.url
        for i in range(good.calendar.view_limit):
            response = self.client.get(secret_url)
            self.assertEquals(response.status_code, 200)

        # a second access is redirected (since view limit is set to 1)
        response = self.client.get(secret_url)
        self.assertEquals(response.status_code, 302)

        # AS EDITORIAL
        self.client.login(username='editor', password='3d1t0r')

        # visit the landing page (the events should appear as proposals)
        url = reverse('eventary:editorial-landing')
        response = self.client.get(url)
        self.assertTrue(good in response.context['proposal_list'])
        self.assertTrue(bad in response.context['proposal_list'])

        # visit the proposal list page (the events should appear)
        url = reverse('eventary:editorial-list_proposals',
                      kwargs={'pk': calendar.pk})
        response = self.client.get(url)
        self.assertTrue(good in response.context['event_list'])
        self.assertTrue(bad in response.context['event_list'])

        # visit the calendar detail view (the events should not appear)
        url = reverse('eventary:anonymous-calendar_details',
                      kwargs={'pk': calendar.pk})
        response = self.client.get(url)
        self.assertFalse(good in response.context['event_list'])
        self.assertFalse(bad in response.context['event_list'])

        # test access rescrition for a proposed event
        url = reverse('eventary:anonymous-proposal_details',
                      kwargs={'pk': good.pk,
                              'calendar_pk': good.calendar.pk,
                              'secret': str(good.secret.secret)})
        for i in range(good.calendar.view_limit+1):
            response = self.client.get(url)
            self.assertEquals(response.status_code, 200)

        # edit the "good" event
        url = reverse('eventary:editorial-update_event',
                      kwargs={'event_pk': good.pk, 'pk': good.calendar.pk})
        response = self.client.get(url)
        self.assertTrue('csrf_token' in response.context, 'no csrf token')
        response = self.client.post(url, {
            'name': 'HostName',
            'phone': 'some phone number',
            'title': 'GoodEvent',
            'csrf_token': response.context['csrf_token'].format(),
            'host': 'Host',
            'start_date': datetime.today().strftime('%Y-%m-%d'),
        })
        good = Event.objects.get(title='GoodEvent')
        with self.assertRaises(Event.DoesNotExist):
            Event.objects.get(title='GoodTestEvent')

        # publish the "good" event
        url = reverse('eventary:editorial-publish_event',
                      kwargs={'pk': good.pk, 'calendar_pk': good.calendar.pk})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302, 'publication redirection')

        # delete the "bad" event
        url = reverse('eventary:editorial-delete_event',
                      kwargs={'pk': bad.pk, 'calendar_pk': bad.calendar.pk})
        response = self.client.get(url)
        self.assertTrue('csrf_token' in response.context, 'no csrf token')
        response = self.client.post(url, {
            'csrf_token': response.context['csrf_token'].format()
        })
        with self.assertRaises(Event.DoesNotExist):
            Event.objects.get(pk=bad.pk)

        # visit the landing page (the events should now appear in other lists)
        url = reverse('eventary:editorial-landing')
        response = self.client.get(url)
        self.assertTrue(good in response.context['event_list'])
        self.assertFalse(bad in response.context['proposal_list'])

        # AS ANONYMOUS
        self.client.logout()

        # visit the published event
        url = reverse('eventary:anonymous-event_details',
                      kwargs={'pk': good.pk, 'calendar_pk': good.calendar.pk})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
