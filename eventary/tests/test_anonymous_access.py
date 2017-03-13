from django.shortcuts import reverse
from django.test import TestCase
from django.urls.exceptions import NoReverseMatch

from .. import urls

from .mixins import AccessTestMixin


class AnonymousUserAccess(AccessTestMixin, TestCase):

    def setUp(self):
        super(AnonymousUserAccess, self).setUp()

        # the special cases need arguments
        self.redirect_special_cases = {
            'editorial-delete_event': {'pk': self.event.pk,
                                       'calendar_pk': self.calendar.pk},
            'editorial-hide_event': {'calendar_pk': self.calendar.pk,
                                     'pk': self.event_to_hide.pk},
            'editorial-list_proposals': {'pk': self.calendar.pk},
            'editorial-publish_event': {'pk': self.proposal.pk,
                                        'calendar_pk': self.calendar.pk},
            'editorial-update_event': {'calendar_pk': self.calendar.pk,
                                       'pk': self.event.pk},
            'management-delete_calendar': {'pk': self.calendar.pk},
            'management-update_calendar': {'pk': self.calendar.pk},
        }
        self.access_special_cases = {
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

        # assert all special cases are dealt
        self.assertEquals(sorted(to_test),
                          sorted(self.redirect_special_cases.keys()))

        # deal all the special cases
        for name, kwargs in self.redirect_special_cases.items():

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

        # assert all special cases are dealt
        self.assertEquals(sorted(to_test),
                          sorted(self.access_special_cases.keys()))

        # deal all the special cases
        for name, kwargs in self.access_special_cases.items():

            # assume status 200 unless a status is given in the kwargs
            status = kwargs.pop('status', 200)

            # assert the status codes
            url = reverse('eventary:{0}'.format(name), kwargs=kwargs)
            response = self.client.get(url)

            self.assertEquals(response.status_code, status)
