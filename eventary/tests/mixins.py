from datetime import datetime
from datetime import timedelta as td

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.test import Client, TestCase

from ..models import Calendar, Event, EventTimeDate, EventHost
from ..models import EventRecurrence, Secret


class AccessTestMixin(TestCase):

    def setUp(self):
        self.client = Client()
        self.calendar = Calendar.objects.create(
            title='TestCalendar',
            view_limit=1,
        )
        self.host = EventHost.objects.create(
            name='TestHost',
            phone='some phone number'
        )
        self.event = Event.objects.create(
            calendar=self.calendar,
            host=self.host,
            title='Event',
            published=True,
        )
        self.proposal = Event.objects.create(
            calendar=self.calendar,
            host=self.host,
            title='Proposal',
            published=False,
        )
        self.event_to_hide = Event.objects.create(
            calendar=self.calendar,
            host=self.host,
            title='EventToHide',
            published=True,
        )
        self.eventtimedate = EventTimeDate.objects.create(
            event=self.event,
            start_date=datetime.today(),
        )
        self.proposaltimedate = EventTimeDate.objects.create(
            event=self.proposal,
            start_date=datetime.today()
        )
        self.eventtohidetimedate = EventTimeDate.objects.create(
            event=self.event_to_hide,
            start_date=datetime.today(),
        )
        self.secret = Secret.objects.create(
            event=self.proposal
        )


class EventTestMixin(TestCase):

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
            location='TestLocation',
            published=True,
            recurring=bool(recurring),
        ) for i in range(nr_events)]

        # create the recurrence objects if needed
        if recurring:
            [EventRecurrence.objects.create(
                event=event,
                recurrences=recurring
            ) for event in events]

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
            location='TestLocation',
            published=False,
            recurring=bool(recurring),
        ) for i in range(nr_events)]

        # create the secrets for the proposals
        [Secret.objects.create(event=proposals[i]) for i in range(nr_events)]

        # create the recurrence objects if needed
        if recurring:
            [EventRecurrence.objects.create(
                event=proposal,
                recurrences=recurring
            ) for proposal in proposals]

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
