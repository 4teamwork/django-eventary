from django.core.urlresolvers import reverse
from django.db.models import Case, IntegerField, Sum, When
from django.views.generic.edit import DeleteView, SingleObjectMixin
from django.views.generic.list import MultipleObjectMixin
from django.views.generic import ListView, View, TemplateView
from django.shortcuts import get_object_or_404, redirect

from .anonymous import CalendarDetailView, EventCreateView
from .anonymous import EventCreateWizardView
from .management import LandingView as ManagementLandingView
from .mixins import EditorialOrManagementRequiredMixin, FilterFormMixin

from ..forms import EventGroupingForm, RecurrenceForm
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

    def get_success_url(self):
        return reverse('eventary:redirector')


class EventEditWizardView(EditorialOrManagementRequiredMixin,
                          EventCreateWizardView):

    model = Event

    def get_context_data(self, form, **kwargs):
        context = super(EventCreateWizardView, self).get_context_data(
            form=form,
            **kwargs
        )

        context.update({'calendar': self.object.calendar})

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

        if (self.steps.current == '2' and
            self.get_cleaned_data_for_step('1').get('recurring')):
            # get the initial values for the EventGroupingForm
            if self.storage.get_step_data('2') is not None:
                context.update({'extraform': RecurrenceForm(
                    self.storage.get_step_data('2'),
                    prefix='recurrence'
                )})
            else:
                eventrecurrence, _ = EventRecurrence.objects.get_or_create(
                    event=self.object
                )
                context.update({'extraform': RecurrenceForm(
                    instance=eventrecurrence,
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

        if image is not None:
            self.object.image.save(image.name, image, save=True)
        if document is not None:
            self.object.document.save(document.name, document, save=True)

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
        if self.object.recurring:
            recurrence = RecurrenceForm(
                self.storage.get_step_data('2'),
                prefix='recurrence',
            ).save(commit=False)
            self.object.eventrecurrence.delete()
            recurrence.event = self.object
            recurrence.save()

        # create the secret for the proposal
        secret, _ = Secret.objects.get_or_create(event=self.object)

        return redirect(
            'eventary:anonymous-proposal_details',
            calendar_pk=self.object.calendar.pk,
            pk=self.object.pk,
            secret=str(secret.secret)
        )


class EventEditView(EditorialOrManagementRequiredMixin, EventCreateView):

    template_name = 'eventary/editorial/update_event.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.event = get_object_or_404(
            Event,
            pk=kwargs.get('event_pk'),
            calendar=self.object
        )
        return super(EventEditView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EventEditView, self).get_context_data(**kwargs)
        context.update({'event': self.event})
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.event = get_object_or_404(
            Event,
            pk=kwargs.get('event_pk'),
            calendar=self.object
        )

        # get the forms
        form_event = self.get_form_event()
        form_timedate = self.get_form_timedate()
        form_grouping = self.get_form_grouping()

        if (form_event.is_valid() and
            form_timedate.is_valid() and
            form_grouping.is_valid()):

            # update the event using the form
            data = form_event.clean()
            data['published'] = False
            Event.objects.filter(pk=kwargs.get('event_pk')).update(**data)
            Secret.objects.get_or_create(
                event=Event.objects.get(pk=kwargs.get('event_pk'))
            )

            # update the times using the form
            data = form_timedate.clean()
            EventTimeDate.objects.filter(
                event=kwargs.get('event_pk')
            ).update(**data)

            # update the groupings using the form
            data = form_grouping.clean()
            self.event.group_set.clear()
            groups = []
            for grouping in data:
                groups += data[grouping]
            self.event.group_set.set(groups)

            return redirect(
                'eventary:anonymous-proposal_details',
                self.object.pk,
                self.event.pk,
                str(Secret.objects.get(event__pk=self.event.pk).secret)
            )

        return super(EventEditView, self).get(request, *args, **kwargs)

    def get_form_event_initial(self):
        return {
            key: getattr(self.event, key)
            for key in [
                'title', 'host', 'location', 'image', 'document',
                'homepage', 'description', 'comment', 'prize',
                'recurring'
            ]
        }

    def get_form_grouping_initial(self):
        to_return = {}
        for group in self.event.group_set.all():
            if group.grouping.title not in to_return:
                to_return[group.grouping.title] = []
            to_return[group.grouping.title].append(group.pk)
        return to_return

    def get_form_timedate_initial(self):
        return {
            key: getattr(self.event.eventtimedate, key)
            for key in [
                'start_date', 'end_date', 'start_time', 'end_time'
            ]
        }


class EventHideView(EditorialOrManagementRequiredMixin,
                    SingleObjectMixin,
                    View):

    model = Event

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.published = False
        # every proposal needs an access secret
        Secret.objects.get_or_create(event=self.object)
        self.object.save()
        return redirect('eventary:redirector')


class EventPublishView(EditorialOrManagementRequiredMixin,
                       SingleObjectMixin,
                       View):

    model = Event

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.published = True
        Secret.objects.filter(event=self.object).delete()
        self.object.save()
        return redirect('eventary:redirector')


class EventListUpdateView(EditorialOrManagementRequiredMixin,
                          MultipleObjectMixin,
                          SingleObjectMixin,
                          FilterFormMixin,
                          TemplateView):

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
        context = super(MultipleObjectMixin, self).get_context_data(
            **kwargs
        )
        context.update({'calendar': self.object})

        event_context = super(EventListUpdateView, self).get_context_data(
            object_list=self.event_list
        )
        proposal_context = super(EventListUpdateView, self).get_context_data(
            object_list=self.proposal_list
        )
        context.update({
            'event_paginator': event_context.get('paginator'),
            'event_page': event_context.get('page_obj'),
            'event_list': event_context.get('object_list'),
            'proposal_paginator': proposal_context.get('paginator'),
            'proposal_page': proposal_context.get('page_obj'),
            'proposal_list': proposal_context.get('object_list'),
        })

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
