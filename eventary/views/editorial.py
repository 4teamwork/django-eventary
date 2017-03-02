from django.core.urlresolvers import reverse
from django.db.models import Case, IntegerField, Sum, When
from django.views.generic.edit import DeleteView, SingleObjectMixin
from django.views.generic import ListView, View
from django.shortcuts import get_object_or_404, redirect

from .anonymous import CalendarDetailView, EventCreateView
from .management import LandingView as ManagementLandingView

from ..models import Calendar, Event, EventTimeDate

from .mixins import EditorialOrManagementRequiredMixin


class CalendarListView(EditorialOrManagementRequiredMixin, ListView):

    model = Calendar
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
            Event.objects.filter(pk=kwargs.get('event_pk')).update(**data)

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

            # redirect the user to the calendar's details
            if self.event.published:
                return redirect(
                    'eventary:anonymous-event_details',
                    self.object.pk,
                    self.event.pk
                )
            else:
                return redirect(
                    'eventary:anonymous-proposal_details',
                    self.object.pk,
                    self.event.pk,
                    str(self.event.secret.secret)
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


class EventPublishView(EditorialOrManagementRequiredMixin,
                       SingleObjectMixin,
                       View):

    model = Event

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.published = True
        self.object.save()
        return redirect('eventary:redirector')


class LandingView(EditorialOrManagementRequiredMixin, ManagementLandingView):

    template_name = 'eventary/editorial/landing.html'


class ProposalListView(EditorialOrManagementRequiredMixin, CalendarDetailView):

    template_name = 'eventary/editorial/list_proposals.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=Calendar.objects.all())
        self.event_list = self.object.event_set.filter(published=False)
        return super(CalendarDetailView, self).get(request, *args, **kwargs)
