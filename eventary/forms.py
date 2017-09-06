from datetime import timedelta

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template.defaultfilters import capfirst
from django.utils.translation import ugettext as _

from datetimepicker.widgets import DateTimePicker
from django_select2.forms import Select2MultipleWidget
from trix.widgets import TrixEditor

from .models import Calendar, Grouping, Group
from .models import Event, EventHost, EventRecurrence


def _datetimepicker_format():

    format_string = settings.DATE_INPUT_FORMATS[0]

    replacements = {'%a': 'dd',
                    '%A': 'dddd',
                    '%w': 'd',
                    '%d': 'DD',
                    '%b': 'MMM',
                    '%B': 'MMMM',
                    '%m': 'MM',
                    '%y': 'YY',
                    '%Y': 'YYYY',
                    '%H': 'HH',
                    '%I': 'hh',
                    '%p': 'A',
                    '%M': 'mm',
                    '%S': 'ss',
                    '%j': 'DDDD',
                    '%U': 'ww',
                    '%W': 'ww'}

    for placeholder, replacement in replacements.items():
        format_string = format_string.replace(placeholder, replacement)

    return format_string


class FilterForm(forms.Form):

    search = forms.CharField(
        label=_('search'),
        required=False,
    )
    from_date = forms.DateField(
        error_messages={'invalid': _('please enter a valid start date')},
        label=_('from'),
        required=False,
        widget=DateTimePicker(
            options={"format": settings.DATE_INPUT_FORMATS[0],
                     "pickTime": False}),
    )
    to_date = forms.DateField(
        error_messages={'invalid': _('please enter a valid end date')},
        label=_('to'),
        required=False,
        widget=DateTimePicker(
            options={"format": settings.DATE_INPUT_FORMATS[0],
                     "pickTime": False}),
    )

    def __init__(self, *args, **kwargs):
        calendar = kwargs.pop('calendar', None)
        super(FilterForm, self).__init__(*args, **kwargs)

        # get the groups
        _groups = Group.objects.filter(
            grouping__calendars=calendar
        ).order_by('grouping').distinct()

        # group the groups by groupings
        _groupings = {}
        for group in _groups:
            # if the group was not added before, do it now
            if group.grouping not in _groupings:
                _groupings[group.grouping] = []
            _groupings[group.grouping].append(group)

        # generate choices using the sorted groupings
        _choices = {
            grouping: [
                (group.pk, group.title) for group in _groupings[grouping]
            ] for grouping in _groupings
        }

        # Now that we have the choices, generate MultipleChoiceFields with them
        _fields = {
            grouping.title: forms.MultipleChoiceField(
                choices=_choices[grouping],
                required=False,
                widget=Select2MultipleWidget,
            ) for grouping in _groupings
        }

        self.filter_field_names = sorted(_fields.keys())

        self.fields.update(_fields)

        for field in self:
            field.field.widget.attrs['placeholder'] = capfirst(field.label)

    def clean(self):
        cleaned_data = super(FilterForm, self).clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')

        if from_date and to_date and from_date > to_date:
            raise forms.ValidationError(
                _('"from date" is greater than "to date"')
            )

        return cleaned_data

    def grouped_groups(self):
        _groups = {}
        if self.is_valid():
            data = self.clean()
            _groups.update({
                grouping: data.get(grouping)
                for grouping in self.filter_field_names
                if len(data.get(grouping))
            })
        return _groups

    def groups(self):
        _groups = []
        if self.is_valid():
            data = self.clean()
            # get all the primary keys of the groups
            for grouping in self.filter_field_names:
                _groups.extend([
                    int(pk)
                    for pk in data.get(grouping)
                ])
        return _groups

    def date_fields(self):
        return [field for field in self if field.name in ['from_date', 'to_date']]  # noqa

    def filter_fields(self):
        return [field for field in self if field.name in self.filter_field_names]  # noqa

    def search_fields(self):
        return [field for field in self if field.name in ['search']]

    class Media:
        css = {'all': ('eventary/css/filterform.css',)}
        js = ('eventary/js/filterform.js',)


class CalendarForm(forms.ModelForm):

    groupings = forms.MultipleChoiceField(
        label=_('groupings'),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    filter_time_span_amount = forms.IntegerField(
        label=_('filter time span amount'),
        required=True,
        min_value=1
    )
    filter_time_span_unit = forms.ChoiceField(
        choices=(('days', _('days')),
                 ('weeks', _('weeks'))),
        label=_('filter time span unit'),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super(CalendarForm, self).__init__(*args, **kwargs)

        self.fields['groupings'].choices = [
            (grouping.pk, grouping.title)
            for grouping in Grouping.objects.all()
        ]

        if self.instance.pk is not None:
            self.fields['groupings'].initial = [
                grouping.pk for grouping in Grouping.objects.filter(
                    calendars=self.instance.pk
                )
            ]

            if not self.instance.filter_time_span.days % 7:
                self.fields['filter_time_span_amount'].initial = self.instance.filter_time_span.days // 7  # noqa
                self.fields['filter_time_span_unit'].initial = 'weeks'
            else:
                self.fields['filter_time_span_amount'].initial = self.instance.filter_time_span.days  # noqa
                self.fields['filter_time_span_unit'].initial = 'days'

    def clean(self):
        data = super().clean()

        invalid_emails = []
        for email in filter(len, map(
                lambda x: x.strip(),
                data.get('notify_on_submission').split('\n'))):
            email = email.strip()
            if len(email):
                try:
                    validate_email(email)
                except ValidationError:
                    invalid_emails.append(email)

        if len(invalid_emails):
            raise ValidationError(
                _('Invalid email addresses: %(invalid_emails)s'),
                params={'invalid_emails': ', '.join(invalid_emails)},
                code='invalid')

        return data

    def save(self, *args, **kwargs):
        super(CalendarForm, self).save(*args, **kwargs)

        data = self.clean()
        groupings = data['groupings']
        for grouping in Grouping.objects.filter(pk__in=groupings):
            grouping.calendars.add(self.instance)

        for grouping in Grouping.objects.exclude(pk__in=groupings):
            grouping.calendars.remove(self.instance)

        self.instance.filter_time_span = timedelta(**{
            data.get('filter_time_span_unit'): data.get('filter_time_span_amount')  # noqa
        })
        self.instance.save()

        return self.instance

    class Meta:
        model = Calendar
        fields = ['title', 'view_limit', 'notify_on_submission',
                  'allow_anonymous_event_proposals']


class EventForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.fields['description'].widget = TrixEditor(
            toolbar_template='eventary/trix/toolbar.html',
        )
        self.fields['entry_fee'].widget = TrixEditor(
            toolbar_template='eventary/trix/toolbar.html',
        )

    class Meta:
        model = Event
        fields = [
            'title', 'location', 'address', 'city', 'zip_code', 'image',
            'document', 'homepage', 'description', 'entry_fee',
        ]

    class Media:
        js = ('eventary/js/trix_loader.js',)


class EventEditorialForm(forms.ModelForm):

    class Meta:
        model = Event
        fields = ['published']


class TimeDateForm(forms.Form):
    start_date = forms.DateField(
        label=_('start date'),
        required=True,
        widget=DateTimePicker(
            attrs={
                'non-recurrence-label': capfirst(_('start date')),
                'recurrence-label': capfirst(_('date of the first recurrence')),  # noqa
            },
            options={'format': settings.DATE_INPUT_FORMATS[0],
                     'pickTime': False}
        )
    )
    end_date = forms.DateField(
        label=_('end date'),
        required=False,
        widget=DateTimePicker(
            attrs={
                'non-recurrence-label': capfirst(_('end date')),
                'recurrence-label': capfirst(_('date of the last recurrence')),
            },
            options={'format': settings.DATE_INPUT_FORMATS[0],
                     'pickTime': False}
        )
    )
    start_time = forms.TimeField(
        label=_('start time'),
        required=False,
        widget=DateTimePicker(options={'format': '%H:%M',
                                       'pickDate': False})
    )
    end_time = forms.TimeField(
        label=_('end time'),
        required=False,
        widget=DateTimePicker(options={'format': '%H:%M',
                                       'pickDate': False})
    )

    def clean(self):
        cleaned_data = super(TimeDateForm, self).clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        def _consistent(start=None, end=None):
            return not end or start and end and start <= end

        # the start date should not be greater than the end date
        if not _consistent(start_date, end_date):
            raise forms.ValidationError(
                _('"start date" cannot be greater than "end date"')
            )

        # you can't know the ending if you don't know the starting
        if end_time and not start_time:
            raise forms.ValidationError(
                _('"start time" cannot be left blank if "end time" is set')
            )

        # check time consistency (end time after start time) on single dates
        if not end_date and not _consistent(start_time, end_time):
            raise forms.ValidationError(
                _('"start time" is greater than "end time"')
            )

        return cleaned_data


class EventGroupingForm(forms.Form):

    def __init__(self, *args, **kwargs):

        calendar = kwargs.pop('calendar', None)

        super(EventGroupingForm, self).__init__(*args, **kwargs)

        if calendar is not None:

            # First we need to get the available groups
            _groups = Group.objects.filter(
                grouping__calendars=calendar
            ).order_by('grouping').distinct()

            # group the groups by grouping
            self._groupings = {}
            for group in _groups:
                # if the group was not added before, do it now
                if group.grouping not in self._groupings:
                    self._groupings[group.grouping] = []
                self._groupings[group.grouping].append(group)

            # Generate choices using the sorted groupings
            self._choices = {
                grouping: [
                    (group.pk, group.title)
                    for group in self._groupings[grouping]
                ] for grouping in self._groupings
            }

            # now update the fields of the form
            self.fields.update({
                # each grouping gets a MultipleChoiceField
                # TODO: replace with SearchableSelect?
                grouping.title: forms.MultipleChoiceField(
                    required=False,
                    widget=Select2MultipleWidget,
                    choices=self._choices[grouping]
                ) for grouping in self._groupings
            })

    class Media:
        css = {'all': ('eventary/css/groupingform.css',)}
        js = ('eventary/js/groupingform.js',)


class HostForm(forms.ModelForm):

    class Meta:
        model = EventHost
        exclude = []


class RecurrenceForm(forms.ModelForm):

    toggler = forms.BooleanField(
        help_text=_('Define the recurrence rules for your event. '
                    'Examples: "Weekly, every Monday and Friday", '
                    '"Monthly, every first Sunday of the month". '
                    'Please consider supplying the date of the first and the '
                    'last occurrence of your event.'),
        label=_('recurring event'),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super(RecurrenceForm, self).__init__(*args, **kwargs)
        self.fields['recurrences'].required = False
        self.fields['recurrences'].label = capfirst(_('recurrences'))

    class Media:
        css = {'all': ('eventary/css/recurrences.css',)}
        js = ('eventary/js/recurrences_wizard.js',)

    class Meta:
        model = EventRecurrence
        fields = ['toggler', 'recurrences']
