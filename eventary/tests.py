from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.shortcuts import reverse
from django.test import Client, TestCase
from django.urls.exceptions import NoReverseMatch

from . import urls
from .models import Calendar, Event, EventTimeDate, Secret


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

    def test_business_logic(self):

        # create an event
        url = reverse('eventary:anonymous-create_event',
                      kwargs={'pk': self.calendar.pk})
        response = self.client.post(url, {
            'title': 'TestEvent',
            'host': 'TestHost',
            'start_date': datetime.today().strftime('%Y-%m-%d'),
        })

        # if creation was successful, then we get a redirection and the
        # response object has an url with the secret
        self.assertEquals(response.status_code, 302)
        self.assertTrue(getattr(response, 'url', False))

        # now access the event with the given secret url
        secret_url = response.url
        response = self.client.get(secret_url)
        self.assertEquals(response.status_code, 200)

        # a second access should be denied (since the view limit is set to 1)
        response = self.client.get(secret_url)
        self.assertEquals(response.status_code, 403)


class EditorialUserAccess(TestCase):

    def setUp(self):
        self.client = Client()
        self.editor = User.objects.create(
            username='editor',
            password=make_password('3d1t0r')
        )
        editorial = Group.objects.get(name='eventary_editorial')
        self.editor.groups.add(editorial)

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

    def login(self, username='editor', password='3d1t0r'):
        return self.client.login(username=username, password=password)

    def test_login(self):
        # check if we can login the user
        self.assertTrue(self.login(), 'could not log in editorial user')

    def test_redirect_when_no_access(self):
        # login the editor
        self.login()

        # some url patterns require arguments, these patterns are stored in
        # `to_test`
        to_test = []

        for urlpattern in urls.urlpatterns:

            if urlpattern.name.startswith('management'):
                try:
                    url = reverse('eventary:{0}'.format(urlpattern.name))
                    response = self.client.get(url)

                    # assert a redirection
                    self.assertEqual(response.status_code,
                                     302,
                                     urlpattern.name)

                except NoReverseMatch:
                    to_test.append(urlpattern.name)

        # the special cases need arguments
        special_cases = {
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
            self.assertEquals(response.status_code, status, name)

    def test_access(self):
        # login the editor
        self.login()

        # some url patterns require arguments, these patterns are stored in
        # `to_test`
        to_test = []

        for urlpattern in urls.urlpatterns:

            if (
                urlpattern.name.startswith('editorial') or
                urlpattern.name.startswith('anonymous')
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
                'pk': self.event.pk,
            },
            'anonymous-export_event_to_ics': {
                'calendar_pk': self.calendar.pk,
                'pk': self.event.pk,
            },
            'anonymous-proposal_details': {
                'calendar_pk': self.calendar.pk,
                'pk': self.proposal.pk,
                'secret': str(self.secret.secret)
            },
            'editorial-delete_event': {
                'calendar_pk': self.calendar.pk,
                'pk': self.proposal.pk,
            },
            'editorial-list_proposals': {
                'pk': self.calendar.pk,
            },
            'editorial-publish_event': {
                'calendar_pk': self.calendar.pk,
                'pk': self.proposal.pk,
                'status': 302,  # the user is redirected after publishing
            },
            'editorial-update_event': {
                'pk': self.calendar.pk,
                'event_pk': self.event.pk,
            }
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

            self.assertEquals(response.status_code,
                              status,
                              name)

    def test_business_logic(self):
        # login the editor
        self.login()

        # view proposal view_limit + 1 times

        # edit the proposal

        # publish the proposal

        # access the published proposal (event details view)

        # edit the published proposal (event)

        # check if the publication status is set to false

        # delete the proposal


class ManagementUserAccess(TestCase):

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create(
            username='manager',
            password=make_password('m4n4g3r')
        )
        management = Group.objects.get(name='eventary_management')
        self.manager.groups.add(management)

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

    def login(self, username='manager', password='m4n4g3r'):
        return self.client.login(username=username, password=password)

    def test_login(self):
        # check if we can login the user
        self.assertTrue(self.login(), 'could not log in management user')

    def test_access(self):
        # login the editor
        self.login()

        # some url patterns require arguments, these patterns are stored in
        # `to_test`
        to_test = []

        for urlpattern in urls.urlpatterns:

            if (
                urlpattern.name.startswith('editorial') or
                urlpattern.name.startswith('anonymous')
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
                'pk': self.event.pk,
            },
            'anonymous-export_event_to_ics': {
                'calendar_pk': self.calendar.pk,
                'pk': self.event.pk,
            },
            'anonymous-proposal_details': {
                'calendar_pk': self.calendar.pk,
                'pk': self.proposal.pk,
                'secret': str(self.secret.secret)
            },
            'editorial-delete_event': {
                'calendar_pk': self.calendar.pk,
                'pk': self.proposal.pk,
            },
            'editorial-list_proposals': {
                'pk': self.calendar.pk,
            },
            'editorial-publish_event': {
                'calendar_pk': self.calendar.pk,
                'pk': self.proposal.pk,
                'status': 302,  # the user is redirected after publishing
            },
            'editorial-update_event': {
                'pk': self.calendar.pk,
                'event_pk': self.event.pk,
            }
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

            self.assertEquals(response.status_code,
                              status,
                              name)

    def test_business_logic(self):
        # login the editor
        self.login()

        # create a calendar
        # update a calendar
        # remove a calendar
