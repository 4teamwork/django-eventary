import os

from django.core.urlresolvers import reverse
from django.db.models import Case, IntegerField, Sum, When
from django.views.generic.edit import DeleteView, SingleObjectMixin
from django.views.generic import ListView, RedirectView, TemplateView
from django.shortcuts import get_object_or_404, redirect

from .anonymous import CalendarDetailView, EventCreateWizardView
from .management import LandingView as ManagementLandingView
from .mixins import EditorialOrManagementRequiredMixin, FilterFormMixin

from .. import emails
from ..forms import EventGroupingForm, RecurrenceForm, FilterForm
from ..models import Calendar, Event, EventTimeDate, Grouping, Secret
from ..models import EventHost, Group, EventRecurrence


class CalendarListView(EditorialOrManagementRequiredMixin, ListView):

    model = Calendar
    paginate_by = 10
    template_name = 'eventary/editorial/list_calendars.html'

    def get_queryset(self):
        qs = super(CalendarListView, self).get_queryset()
        qs = qs.annotate(
            num_events=Sum(Case(When(
                event__published=True,
                then=1
            )), output_field=IntegerField(), distinct=True),
            num_proposals=Sum(Case(When(
                event__published=False,
                then=1
            )), output_field=IntegerField(), distinct=True),
        )
        return qs


class EventDeleteView(EditorialOrManagementRequiredMixin, DeleteView):

    model = Event
    template_name = 'eventary/editorial/delete_event.html'

    def post(self, request, *args, **kwargs):
        response = super(EventDeleteView, self).post(request, *args, **kwargs)
        if self.object.host.notify:
            emails.notify_delete(self.object)
        return response

    def get_success_url(self):
        return reverse('eventary:redirector')


class EventEditWizardView(EditorialOrManagementRequiredMixin,
                          EventCreateWizardView):

    model = Event

    def get_context_data(self, form, **kwargs):
        # yes! we're using getting the context from the EventCreateWizardView
        # super class. This is because the model (for the single object mixing
        # changes from Calendar to Event).
        context = super(EventCreateWizardView, self).get_context_data(
            form=form,
            **kwargs
        )

        context.update({
            'calendar': self.object.calendar,
            'wizard_steps_named': [
                (str(i), self.form_names[i])
                for i in range(len(self.form_names))
            ],
            'valid_steps': [
                str(i)
                for i in range(len(self.form_list))
            ],
        })

        if (self.steps.current == '1' and
            self.object.calendar.grouping_set.count()):
            # get the initial values for the EventGroupingForm
            if self.storage.get_step_data('1') is not None:
                context.update({'extraform': EventGroupingForm(
                    self.storage.get_step_data('1'),
                    calendar=self.object.calendar,
                    prefix='grouping'
                )})
            else:
                groups = self.object.group_set.all()
                context.update({'extraform': EventGroupingForm(
                    calendar=self.object.calendar,
                    prefix='grouping',
                    initial={
                        grouping.title: [
                            group.pk
                            for group in groups
                            if group.grouping == grouping
                        ]
                        for grouping in Grouping.objects.filter(
                            group__in=groups
                        )
                    }
                )})

        if (self.steps.current == '2'):
            if self.storage.get_step_data('2') is not None:
                context.update({'extraform_first': RecurrenceForm(
                    self.storage.get_step_data('2'),
                    prefix='recurrence'
                )})
            else:
                if self.object.recurring:
                    eventrecurrence, _ = EventRecurrence.objects.get_or_create(
                        event=self.object
                    )
                    context.update({'extraform_first': RecurrenceForm(
                        initial={'toggler': True},
                        instance=eventrecurrence,
                        prefix='recurrence'
                    )})
                else:
                    context.update({'extraform_first': RecurrenceForm(
                        prefix='recurrence'
                    )})

        return context

    def get_form_initial(self, step):
        if step == '2':
            return self.object.eventtimedate.__dict__

    def get_form_instance(self, step):
        if step == '0':
            return self.object.host
        if step == '1':
            return self.object

    def done(self, form_list, form_dict, **kwargs):

        # update the host
        data = form_dict['0'].clean()
        EventHost.objects.filter(event__pk=self.object.pk).update(**data)

        # update the event
        data = form_dict['1'].clean()
        image = data.pop('image', None)
        document = data.pop('document', None)
        data['published'] = False
        Event.objects.filter(pk=self.object.pk).update(**data)
        self.object = Event.objects.get(pk=self.object.pk)

        def _file_name(_f):
            """returns a truncated version of the file's name"""
            return os.path.split(_f)[1][-15:]

        if image is not None:
            self.object.image.save(_file_name(image.name), image, save=True)
        if document is not None:
            self.object.document.save(_file_name(document.name),
                                      document,
                                      save=True)

        # update the time and date
        data = form_dict['2'].clean()
        EventTimeDate.objects.filter(event__pk=self.object.pk).update(**data)

        # store the grouping information
        if self.object.calendar.grouping_set.count():

            # remove the event from all the groups
            self.object.group_set.clear()

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
                    group.events.add(self.object)
                    group.save()

        # store the recurrence information
        recurrence_form = RecurrenceForm(self.storage.get_step_data('2'),
                                         prefix='recurrence')
        assert recurrence_form.is_valid()

        if self.object.recurring:
            self.object.eventrecurrence.delete()

        if recurrence_form.clean().get('toggler'):
            self.object.recurring = True
            self.object.save()
            recurrence = recurrence_form.save(commit=False)
            recurrence.event = self.object
            recurrence.save()
        else:
            self.object.recurring = False
            self.object.save()

        # create the secret for the proposal
        secret, _ = Secret.objects.get_or_create(event=self.object)

        if self.object.host.notify:
            emails.notify_update(self.object)

        # prepare for redirection
        self.calendar = self.object.calendar
        self.event = self.object
        self.secret = secret
        return redirect(self.get_success_url())


class EventHideView(EditorialOrManagementRequiredMixin,
                    SingleObjectMixin,
                    RedirectView):

    model = Event

    def dispatch(self, request, *args, **kwargs):
        response = super(EventHideView, self).dispatch(request,
                                                       *args,
                                                       **kwargs)
        if self.object.host.notify:
            emails.notify_hide(self.object)
        return response

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.published = False
        # every proposal needs an access secret
        Secret.objects.get_or_create(event=self.object)
        self.object.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('eventary:redirector')


class EventPublishView(EditorialOrManagementRequiredMixin,
                       SingleObjectMixin,
                       RedirectView):

    model = Event

    def dispatch(self, request, *args, **kwargs):
        response = super(EventPublishView, self).dispatch(request,
                                                          *args,
                                                          **kwargs)
        if self.object.host.notify:
            emails.notify_publish(self.object)
        return response

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.published = True
        Secret.objects.filter(event=self.object).delete()
        self.object.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('eventary:redirector')


class EventListUpdateView(EditorialOrManagementRequiredMixin,
                          SingleObjectMixin,
                          FilterFormMixin,
                          TemplateView):

    form_class = FilterForm
    model = Calendar
    paginate_by = 10
    template_name = 'eventary/editorial/publish_event_list.html'

    def get_objects(self):
        self.object = self.get_object()
        self.object_list = None
        self.event_list = self.object.event_set.filter(
            published=True
        ).distinct()
        self.proposal_list = self.object.event_set.filter(
            published=False
        ).distinct()

    def dispatch(self, request, *args, **kwargs):
        self.get_objects()
        return super(EventListUpdateView, self).dispatch(request,
                                                         *args,
                                                         **kwargs)

    def post(self, request, *args, **kwargs):
        for action in set(request.POST.keys() - {'csrfmiddlewaretoken', 'pk'}):
            if action in ['publish', 'hide', 'delete']:
                _action_method = getattr(self, action)
                _action_method(request)
        self.get_objects()
        return super(EventListUpdateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EventListUpdateView, self).get_context_data(
            **kwargs
        )
        context.update({'calendar': self.object})
        return context

    def publish(self, request):
        proposals = self.proposal_list.filter(
            pk__in=request.POST.getlist('pk')
        )
        Secret.objects.filter(event__in=proposals).delete()
        proposals.update(published=True)

    def hide(self, request):
        # hide the events
        events = self.event_list.filter(pk__in=request.POST.getlist('pk'))
        [Secret.objects.get_or_create(event=event) for event in events]
        events.update(published=False)
        # recreate their secrets

    def delete(self, request):
        proposals = self.proposal_list.filter(
            pk__in=request.POST.getlist('pk')
        )
        Secret.objects.filter(event__in=proposals).delete()
        proposals.delete()

    def get_form(self):

        form_class = self.get_form_class()

        if len(self.request.GET):
            self.form = form_class(self.request.GET,
                                   calendar=self.object,
                                   prefix='filter')
        else:
            self.form = form_class(calendar=self.object,
                                   initial=self.initial,
                                   prefix='filter')
        return self.form


class LandingView(EditorialOrManagementRequiredMixin, ManagementLandingView):

    template_name = 'eventary/editorial/landing.html'


class ProposalListView(EditorialOrManagementRequiredMixin, CalendarDetailView):

    template_name = 'eventary/editorial/list_proposals.html'

    def __init__(self, *args, **kwargs):
        super(ProposalListView, self).__init__(*args, **kwargs)
        self.event_list = Event.objects.filter(published=False).distinct()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=Calendar.objects.all())
        self.event_list.filter(calendar=self.object)
        return super(ProposalListView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProposalListView, self).get_context_data(**kwargs)

        page, paginator = self.paginate_qs(self.event_list,
                                           prefix='proposal')
        # update the context
        context.update({'paginator': paginator,
                        'page': page})

        return context
