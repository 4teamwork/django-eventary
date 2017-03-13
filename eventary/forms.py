import datetime

from django import forms
from django.utils.translation import ugettext as _

from bootstrap3_datetime.widgets import DateTimePicker
from django_select2.forms import Select2MultipleWidget

from .models import Calendar, Grouping, Group
from .models import Event, EventHost, EventRecurrence


class GenericFilterForm(forms.Form):

    from_date = forms.DateField(
        label=_('from'),
        required=False,
        widget=DateTimePicker(options={"format": "YYYY-MM-DD",
                                       "pickTime": False})
    )
    to_date = forms.DateField(
        label=_('to'),
        required=False,
        widget=DateTimePicker(options={"format": "YYYY-MM-DD",
                                       "pickTime": False})
    )

    def __init__(self, *args, **kwargs):
        super(GenericFilterForm, self).__init__(*args, **kwargs)

        # group the groups by groupingstypes
        _groupings = {}
        for group in Group.objects.all():
            # if the group was not added before, do it now
            if group.grouping.grouping_type not in _groupings:
                _groupings[group.grouping.grouping_type] = []
            _groupings[group.grouping.grouping_type].append(group)

        # generate choices using the sorted groupings
        _choices = {
            grouping: [
                (group.pk, group.title) for group in _groupings[grouping]
            ] for grouping in _groupings
        }

        # Now that we have the choices, generate MultipleChoiceFields with them
        _fields = {
            grouping.label: forms.MultipleChoiceField(
                required=False,
                widget=Select2MultipleWidget,
                choices=_choices[grouping],
            ) for grouping in _groupings
        }

        self.fields.update(_fields)

    def clean(self):
        cleaned_data = super(GenericFilterForm, self).clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')

        if from_date and to_date and from_date > to_date:
            raise forms.ValidationError(
                _('"from date" is greater than "to date"')
            )
        return cleaned_data

    def groups(self):
        groups = []
        if self.is_valid():
            # get all the primary keys of the groups
            data = self.clean()
            for grouping in data:
                if (
                    data[grouping] is not None and
                    not isinstance(data[grouping], datetime.date)
                ):
                    groups.extend([int(pk) for pk in data[grouping]])
        return groups


class FilterForm(forms.Form):

    from_date = forms.DateField(
        label=_('from'),
        required=False,
        widget=DateTimePicker(options={"format": "YYYY-MM-DD",
                                       "pickTime": False})
    )
    to_date = forms.DateField(
        label=_('from'),
        required=False,
        widget=DateTimePicker(options={"format": "YYYY-MM-DD",
                                       "pickTime": False})
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
                required=False,
                widget=Select2MultipleWidget,
                choices=_choices[grouping]
            ) for grouping in _groupings
        }

        self.fields.update(_fields)

    def clean(self):
        cleaned_data = super(GenericFilterForm, self).clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')

        if from_date and to_date and from_date > to_date:
            raise forms.ValidationError(
                _('"from date" is greater than "to date"')
            )
        return cleaned_data

    def groups(self):
        groups = []
        if self.is_valid():
            # get all the primary keys of the groups
            data = self.clean()
            for grouping in data:
                if (
                    data[grouping] is not None and
                    not isinstance(data[grouping], datetime.date)
                ):
                    groups.extend([int(pk) for pk in data[grouping]])
        return groups


class CalendarForm(forms.ModelForm):

    groupings = forms.MultipleChoiceField(
        label=_('groupings'),
        required=False,
        widget=forms.CheckboxSelectMultiple
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

    def save(self, *args, **kwargs):
        super(CalendarForm, self).save(*args, **kwargs)

        data = self.clean()
        groupings = data['groupings']
        for grouping in Grouping.objects.filter(pk__in=groupings):
            grouping.calendars.add(self.instance)

        for grouping in Grouping.objects.exclude(pk__in=groupings):
            grouping.calendars.remove(self.instance)

        return self.instance

    class Meta:
        model = Calendar
        fields = ['title', 'view_limit']


class EventForm(forms.ModelForm):

    class Meta:
        model = Event
        fields = ['title', 'location', 'image', 'document', 'homepage',
                  'description', 'comment', 'prize', 'recurring']


class EventEditorialForm(forms.ModelForm):

    class Meta:
        model = Event
        fields = ['published']


class TimeDateForm(forms.Form):
    start_date = forms.DateField(
        label=_('start date'),
        required=True,
        widget=DateTimePicker(options={"format": "YYYY-MM-DD",
                                       "pickTime": False})
    )
    start_time = forms.TimeField(
        label=_('start time'),
        required=False,
        widget=DateTimePicker(options={"format": "HH:mm",
                                       "pickDate": False})
    )
    end_date = forms.DateField(
        label=_('end date'),
        required=False,
        widget=DateTimePicker(options={"format": "YYYY-MM-DD",
                                       "pickTime": False})
    )
    end_time = forms.TimeField(
        label=_('end time'),
        required=False,
        widget=DateTimePicker(options={"format": "HH:mm",
                                       "pickDate": False})
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
                    widget=forms.CheckboxSelectMultiple,
                    choices=self._choices[grouping]
                ) for grouping in self._groupings
            })

    class Media:
        css = {'all': ('css/groupingform.css',)}
        js = ('js/groupingform.js',)


class HostForm(forms.ModelForm):

    class Meta:
        model = EventHost
        exclude = []


class RecurrenceForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(RecurrenceForm, self).__init__(*args, **kwargs)
        self.fields['recurrences'].required = False

    class Media:
        css = {'all': ('css/recurrences.css',)}
        js = ('js/recurrences_wizard.js',)

    class Meta:
        model = EventRecurrence
        fields = ['recurrences']
