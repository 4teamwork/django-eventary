from collections import OrderedDict
from datetime import datetime
from os.path import join

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import Case, IntegerField, Sum, When
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, TemplateView
from django.views.generic.detail import SingleObjectMixin

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


class EventCreateWizardView(SingleObjectMixin, SessionWizardView):

    file_storage = FileSystemStorage(location=join(settings.MEDIA_ROOT,
                                                   'uploads'))
    form_list = [HostForm, EventForm, TimeDateForm]
    form_names = [_('host information'),
                  _('event information'),
                  _('date and time information')]
    model = Calendar
    template_name = 'eventary/anonymous/create_event_wizard.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(EventCreateWizardView, self).get(request, *args, **kwargs)

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

        context.update({
            'wizard_steps_named': [
                (str(i), self.form_names[i])
                for i in range(len(self.form_names))
            ],
            'valid_steps': [
                str(i)
                for i in range(len(self.form_list))
                if self.get_cleaned_data_for_step(str(i)) is not None
            ],
        })

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

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        super_response = super(EventCreateWizardView, self).post(request,
                                                                 *args,
                                                                 **kwargs)

        wizard_goto_step = self.request.POST.get('wizard_submit_and_goto_step',
                                                 None)
        if wizard_goto_step and wizard_goto_step in self.get_form_list():
            return self.render_goto_step(wizard_goto_step)
        else:
            return super_response

    def render_done(self, form, **kwargs):

        final_forms = OrderedDict()

        for form_key in self.get_form_list():
            form_obj = self.get_form(
                step=form_key,
                data=self.storage.get_step_data(form_key),
                files=self.storage.get_step_files(form_key),
            )
            if not form_obj.is_valid():
                return self.render_revalidation_failure(form_key,
                                                        form_obj,
                                                        **kwargs)
            final_forms[form_key] = form_obj

        wizard_goto_step = self.request.POST.get('wizard_submit_and_goto_step',
                                                 None)
        if wizard_goto_step and wizard_goto_step in self.get_form_list():
            return self.render_goto_step(wizard_goto_step)
        else:
            done_response = self.done(final_forms.values(),
                                      form_dict=final_forms,
                                      **kwargs)
            self.storage.reset()
            return done_response


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
