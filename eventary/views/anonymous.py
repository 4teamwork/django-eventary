from datetime import datetime

from django.db.models import Case, IntegerField, Sum, When
from django.views.generic import DetailView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.shortcuts import get_object_or_404, redirect

from ..forms import EventForm, TimeDateForm, EventGroupingForm, HostForm
from ..forms import RecurrenceForm
from ..models import Calendar, Event, EventTimeDate, Group, Secret

from .mixins import EventFilterFormMixin


class CalendarDetailView(EventFilterFormMixin,
                         SingleObjectMixin,
                         TemplateView):

    model = Calendar
    template_name = 'eventary/anonymous/calendar_details.html'

    def __init__(self, *args, **kwargs):
        super(CalendarDetailView, self).__init__(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=Calendar.objects.all())
        return super(CalendarDetailView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CalendarDetailView, self).get_context_data(**kwargs)
        context['calendar'] = self.object

        self.event_list = self.event_list.filter(calendar=self.object)

        page, paginator = self.paginate_qs(self.event_list)

        # update the context
        context.update({
            'paginator': paginator,
            'page': page,
            'object_list': self.event_list,
            'event_list': self.event_list
        })

        return context

    def get_form_kwargs(self):
        kwargs = {'initial': self.get_initial()}
        if len(self.request.GET):
            kwargs.update({
                'data': self.request.GET
            })
        return kwargs


class EventCreateView(SingleObjectMixin, TemplateView):

    model = Calendar
    template_name = 'eventary/anonymous/create_event.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(EventCreateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EventCreateView, self).get_context_data(**kwargs)

        context.update({
            'calendar': self.object,
            'eventform': self.get_form_event(),
            'timedateform': self.get_form_timedate(),
            'recurrenceform': self.get_form_recurrence(),
            'hostform': self.get_form_host(),
            'groupingform': self.get_form_grouping()
        })

        return context

    def get_form_event(self):
        get_initial = getattr(self, 'get_form_event_initial', lambda: {})
        if self.request.method == 'POST':
            self.event_form = EventForm(
                self.request.POST,
                self.request.FILES,
                initial=get_initial()
            )
        else:
            self.event_form = EventForm(initial=get_initial())
        return self.event_form

    def get_form_grouping(self):
        get_initial = getattr(self, 'get_form_grouping_initial', lambda: {})
        if self.request.method == 'POST':
            self.grouping_form = EventGroupingForm(
                self.request.POST,
                calendar=self.object,
                initial=get_initial()
            )
        else:
            self.grouping_form = EventGroupingForm(
                calendar=self.object,
                initial=get_initial()
            )
        return self.grouping_form

    def get_form_host(self):
        get_initial = getattr(self, 'get_form_host_initial', lambda: {})
        if self.request.method == 'POST':
            self.host_form = HostForm(self.request.POST,
                                      initial=get_initial())
        else:
            self.host_form = HostForm(initial=get_initial())
        return self.host_form

    def get_form_recurrence(self):
        get_initial = getattr(self, 'get_form_recurrence_initial', lambda: {})
        if (self.request.method == 'POST' and
            'recurrences' in self.request.POST):
            self.recurrence_form = RecurrenceForm(self.request.POST,
                                                  initial=get_initial())
        else:
            self.recurrence_form = RecurrenceForm(initial=get_initial())
        return self.recurrence_form

    def get_form_timedate(self):
        get_initial = getattr(self, 'get_form_timedate_initial', lambda: {})
        if self.request.method == 'POST':
            self.timedate_form = TimeDateForm(
                self.request.POST,
                initial=get_initial()
            )
        else:
            self.timedate_form = TimeDateForm(initial=get_initial())
        return self.timedate_form

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # get the forms
        form_event = self.get_form_event()
        form_timedate = self.get_form_timedate()
        form_recurrence = self.get_form_recurrence()
        form_host = self.get_form_host()
        form_grouping = self.get_form_grouping()

        if (form_event.is_valid() and
            form_timedate.is_valid() and
            form_host.is_valid() and
            form_grouping.is_valid()):

            # create the host
            host = form_host.save()

            # prepare the event and store it
            event = form_event.save(commit=False)
            event.calendar = self.object
            event.host = host
            event.published = False
            event.save()

            # if the event is recurring, create the recurrence instance
            if event.recurring and form_recurrence.is_valid():
                recurrence = form_recurrence.save(commit=False)
                recurrence.event = event
                recurrence.save()

            # create the time date objects for the event
            timedatedata = form_timedate.clean()
            timedate = EventTimeDate()
            timedate.event = event
            timedate.start_date = timedatedata['start_date']

            if timedatedata['start_time'] is not None:
                timedate.start_time = timedatedata['start_time']

            if timedatedata['end_date'] is not None:
                timedate.end_date = timedatedata['end_date']

            if timedatedata['end_time'] is not None:
                timedate.end_time = timedatedata['end_time']

            timedate.save()

            # associate the event to the groups given by the groupingform
            groupingdata = form_grouping.clean()
            for grouping in groupingdata:
                for group_pk in groupingdata[grouping]:
                    group = get_object_or_404(
                        Group,
                        pk=int(group_pk),
                        grouping__title=grouping
                    )

                    group.events.add(event)
                    group.save()

            # create a secret to let annonymous users access the proprosal
            secret = Secret.objects.create(event=event)

            # redirect the user to the calendar's details
            return redirect(
                'eventary:anonymous-proposal_details',
                calendar_pk=self.object.pk,
                pk=event.pk,
                secret=str(secret.secret)
            )

        return super(EventCreateView, self).get(request, *args, **kwargs)


class EventDetailView(DetailView):

    model = Event
    queryset = Event.objects.filter(published=True)
    template_name = 'eventary/anonymous/published_event.html'

    def get_context_data(self, **kwargs):
        context = super(EventDetailView, self).get_context_data(**kwargs)

        groupings = {}
        for group in self.object.group_set.distinct():
            if group.grouping not in groupings:
                groupings[group.grouping] = []
            groupings[group.grouping].append(group)

        context.update({
            'timedates': self.object.eventtimedate,
            'groupings': groupings
        })

        return context


class EventICSExportView(EventDetailView):

    content_type = 'text/calendar'
    template_name = 'eventary/anonymous/published_event.ics'


class LandingView(EventFilterFormMixin, TemplateView):

    template_name = 'eventary/anonymous/landing.html'

    def get_context_data(self, **kwargs):
        context = super(LandingView, self).get_context_data(**kwargs)

        # general context data
        context.update({
            'calendar_list':  self.get_queryset(),
            'event_count':    Event.objects.filter(published=True).count(),
            'timedate_count': EventTimeDate.objects.count()
        })

        # create some paginators
        event_page, event_paginator = self.paginate_qs(
            self.event_list,
            prefix='event'
        )

        context.update({'event_page': event_page,
                        'event_list': self.event_list,
                        'event_paginator': event_paginator})

        return context

    def get_queryset(self):
        qs = Calendar.objects.annotate(
            num_events=Sum(Case(When(
                event__published=True,
                then=1
            )), output_field=IntegerField(), distinct=True),
        ).order_by()
        return qs


class ProposalDetailView(EventDetailView):

    queryset = Event.objects.filter(published=False)
    template_name = 'eventary/anonymous/proposed_event.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # try to get the secret from kwargs or GET params
        self.secret = get_object_or_404(
            Secret,
            secret=kwargs.get('secret',
                              request.GET.get('secret', None))
        )

        # update the secret's
        today = datetime.today().date()
        if self.secret.last_call != today:
            self.secret.calls = 0

        # check if the maximum number of anonymous views per day is reached
        if request.user.is_anonymous():
            self.secret.last_call = today
            self.secret.calls += 1
            self.secret.save()
            if self.secret.calls > self.secret.event.calendar.view_limit:
                return redirect('eventary:anonymous-too_many_views')

        # try to get the event for the given calendar and secret
        self.event = get_object_or_404(
            Event,
            calendar__pk=kwargs.get('calendar_pk'),
            pk=kwargs.get('pk'),
            secret=self.secret
        )

        return super(ProposalDetailView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProposalDetailView, self).get_context_data(**kwargs)
        context.update({
            'secret': self.secret,
            'calendar': self.object.calendar,
        })
        return context


class TooManyViewsView(TemplateView):

    template_name = 'eventary/anonymous/too_many_views.html'
