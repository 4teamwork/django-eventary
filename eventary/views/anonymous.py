from datetime import datetime
from os.path import join

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import Case, IntegerField, Sum, When
from django.views.generic import DetailView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.shortcuts import get_object_or_404, redirect

from formtools.wizard.views import SessionWizardView

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

        page, paginator = self.paginate_qs(self.event_list,
                                           prefix='event')

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


class EventCreateWizardView(SingleObjectMixin, SessionWizardView):

    file_storage = FileSystemStorage(location=join(settings.MEDIA_ROOT,
                                                   'uploads'))
    form_list = [HostForm, EventForm, TimeDateForm]
    model = Calendar
    template_name = 'eventary/anonymous/create_event_wizard.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(EventCreateWizardView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(EventCreateWizardView, self).post(request,
                                                       *args,
                                                       **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super(EventCreateWizardView, self).get_context_data(
            form=form,
            **kwargs
        )

        if (self.steps.current == '1' and
            self.object.grouping_set.count()):
            # get the initial values for the EventGroupingForm
            if self.storage.get_step_data('1') is not None:
                context.update({'extraform': EventGroupingForm(
                    self.storage.get_step_data('1'),
                    calendar=self.object,
                    prefix='grouping'
                )})
            else:
                context.update({'extraform': EventGroupingForm(
                    calendar=self.object,
                    prefix='grouping'
                )})

        if (self.steps.current == '2' and
            self.get_cleaned_data_for_step('1').get('recurring')):
            # get the initial values for the EventGroupingForm
            if self.storage.get_step_data('2') is not None:
                context.update({'extraform': RecurrenceForm(
                    self.storage.get_step_data('2'),
                    prefix='recurrence'
                )})
            else:
                context.update({'extraform': RecurrenceForm(
                    prefix='recurrence'
                )})
        return context

    def done(self, form_list, form_dict, **kwargs):

        # store the host
        host = form_dict['0'].save()

        # prepare the event and store it
        event = form_dict['1'].save(commit=False)
        event.calendar = self.object
        event.host = host
        event.published = False
        event.save()

        # store the grouping information
        if self.object.grouping_set.count():

            # prepare the data
            data = self.storage.get_step_data('1')
            groupingdata = {
                grouping.split('grouping-')[-1]: data.getlist(grouping)
                for grouping in data
                if 'grouping-' in grouping
            }

            # do some grouping
            for grouping in groupingdata:
                for group_pk in groupingdata[grouping]:
                    group = get_object_or_404(
                        Group,
                        pk=int(group_pk),
                        grouping__title=grouping
                    )
                    group.events.add(event)
                    group.save()

        # store the timedate information
        timedate, _ = EventTimeDate.objects.get_or_create(
            event=event,
            **form_dict['2'].clean()
        )

        # store the recurrence information
        if event.recurring:
            recurrence = RecurrenceForm(
                self.storage.get_step_data('2'),
                prefix='recurrence',
            ).save(commit=False)
            recurrence.event = event
            recurrence.save()

        # create the secret for the proposal
        secret, _ = Secret.objects.get_or_create(event=event)

        return redirect(
            'eventary:anonymous-proposal_details',
            calendar_pk=self.object.pk,
            pk=event.pk,
            secret=str(secret.secret)
        )


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

        # get the list of calendars
        self.calendar_list = self.get_queryset()

        # create some paginators
        calendar_page, calendar_paginator = self.paginate_qs(
            self.calendar_list,
            prefix='calendar'
        )
        event_page, event_paginator = self.paginate_qs(self.event_list,
                                                       prefix='event')

        # general context data
        context.update({'calendar_list': self.calendar_list,
                        'calendar_page': calendar_page,
                        'calendar_paginator': calendar_paginator,
                        'event_page': event_page,
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
