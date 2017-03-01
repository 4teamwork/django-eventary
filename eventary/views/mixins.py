from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.views.generic.edit import FormMixin

from ..forms import GenericFilterForm
from ..models import Event


class ManagementRequiredMixin(PermissionRequiredMixin):

    def has_permission(self):
        return self.request.user.groups.filter(
            name='eventary_management'
        ).exists()


class EditorialOrManagementRequiredMixin(PermissionRequiredMixin):

    def has_permission(self):
        return self.request.user.groups.filter(name__in=[
            'eventary_editorial',
            'eventary_management'
        ]).exists()


class EventFilterFormMixin(FormMixin):

    def __init__(self, **kwargs):
        super(EventFilterFormMixin, self).__init__(**kwargs)

        # events
        self.event_list = Event.objects.filter(published=True).distinct()

    def apply_filter(self, form):

        self.event_list = self.event_list.filter(self.get_date_filter(form))

        # filter the queryset by the selected groups
        groups = form.groups()
        if len(groups) > 0:
            self.event_list = self.event_list.filter(group__in=groups)

    def get(self, request, *args, **kwargs):

        form = self.get_form()
        if len(self.request.GET) and form.is_valid():
            self.apply_filter(form)

        context = self.get_context_data()

        return self.render_to_response(context)

    def get_date_filter(self, form):
        data = form.clean()

        fdate = data.get('from_date', None)
        tdate = data.get('to_date', None)

        # find the right filter
        if fdate is not None and tdate is not None:
            return (Q(recurring=False,
                      eventtimedate__start_date__gte=fdate,
                      eventtimedate__start_date__lte=tdate,
                      eventtimedate__end_date__isnull=True) |
                    Q(recurring=False,
                      eventtimedate__start_date__gte=fdate,
                      eventtimedate__end_date__isnull=False,
                      eventtimedate__end_date__gte=fdate,
                      eventtimedate__end_date__lte=tdate) |
                    Q(recurring=True,
                      eventtimedate__start_date__gte=fdate,
                      eventtimedate__start_date__lte=tdate,
                      eventtimedate__end_date__isnull=False) |
                    Q(recurring=True,
                      eventtimedate__end_date__gte=fdate,
                      eventtimedate__end_date__lte=tdate,
                      eventtimedate__end_date__isnull=False))
        elif tdate is not None:
            return (Q(recurring=False,
                      eventtimedate__start_date__lte=tdate,
                      eventtimedate__end_date__isnull=True) |
                    Q(recurring=False,
                      eventtimedate__end_date__isnull=False,
                      eventtimedate__end_date__lte=tdate) |
                    Q(recurring=True,
                      eventtimedate__start_date__lte=tdate,
                      eventtimedate__end_date__isnull=False))
        elif fdate is not None:
            return (Q(recurring=False,
                      eventtimedate__start_date__gte=fdate) |
                    Q(recurring=True,
                      eventtimedate__end_date__gte=fdate))

        return Q()

    def get_form(self):
        if len(self.request.GET):
            self.form = GenericFilterForm(self.request.GET, prefix='filter')
        else:
            self.form = GenericFilterForm(prefix='filter')
        return self.form

    def paginate_qs(self, qs, prefix='paginator'):
        paginator = Paginator(qs, 10)

        page = self.request.GET.get('{0}_page'.format(prefix), 1)
        try:
            obj_list = paginator.page(page)
        except PageNotAnInteger:
            obj_list = paginator.page(1)
        except EmptyPage:
            obj_list = paginator.page(paginator.num_pages)

        return obj_list, paginator


class FilterFormMixin(EventFilterFormMixin):

    def __init__(self, **kwargs):
        super(FilterFormMixin, self).__init__(**kwargs)

        # proposals
        self.proposal_list = Event.objects.filter(published=False).distinct()

    def apply_filter(self, form):
        super(FilterFormMixin, self).apply_filter(form)

        self.proposal_list = self.proposal_list.filter(self.get_date_filter(
            form
        ))

        # filter the queryset by the selected groups
        groups = form.groups()
        if len(groups) > 0:
            self.proposal_list = self.proposal_list.filter(group__in=groups)
