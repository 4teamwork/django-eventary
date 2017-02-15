from django.core.urlresolvers import reverse
from django.views.generic.edit import DeleteView, SingleObjectMixin
from django.views.generic import View
from django.shortcuts import get_object_or_404, redirect

from .anonymous import CalendarDetailView, EventCreateView
from .management import LandingView as ManagementLandingView
from .management import CalendarListView as ManagementCalendarListView

from ..models import Event


class CalendarListView(ManagementCalendarListView):

    template_name = 'eventary/editorial/list_calendars.html'


class EventDeleteView(DeleteView):

    model = Event
    template_name = 'eventary/editorial/delete_event.html'

    def get_success_url(self):
        return reverse('eventary:redirector')


class EventEditView(EventCreateView):

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
        form_grouping = self.get_form_grouping()

        if (form_event.is_valid() and form_grouping.is_valid()):
            # update the event using the form
            data = form_event.clean()
            Event.objects.filter(pk=kwargs.get('event_pk')).update(**data)

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


class EventPublishView(SingleObjectMixin, View):

    model = Event

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.published = True
        self.object.save()
        return redirect('eventary:redirector')


class LandingView(ManagementLandingView):

    template_name = 'eventary/editorial/landing.html'


class ProposalListView(CalendarDetailView):

    template_name = 'eventary/editorial/list_proposals.html'

    def get_queryset(self):
        return self.object.event_set.filter(published=False)
