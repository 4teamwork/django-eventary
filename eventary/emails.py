from django.conf import settings
from django.core.mail import send_mail
from django.template.defaultfilters import capfirst
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _


def notify_calendar_admins(receivers, event):

    subject = _('A new event has been submitted')

    context = {
        'event': event,
    }
    txt_message = render_to_string(
        'eventary/email/notify_calendar_admin.txt',
        context,
    )
    html_message = render_to_string(
        'eventary/email/notify_calendar_admin.html',
        context,
    )

    send_mail(
        subject,
        txt_message,
        settings.DEFAULT_FROM_EMAIL,
        receivers,
        html_message=html_message
    )


def _event_notification(receiver, event, verb):

    if type(receiver) is not list:
        receiver = [receiver]

    # prepare the subject
    subject = capfirst(_('your event has been {verb}').format(verb=_(verb)))

    # prepare the messages
    context = {
        'host': event.host,
        'event': event,
    }
    txt_message = render_to_string(
        'eventary/email/event_{verb}.txt'.format(verb=verb),
        context,
    )
    html_message = render_to_string(
        'eventary/email/event_{verb}.html'.format(verb=verb),
        context,
    )

    # send the email
    send_mail(
        subject,
        txt_message,
        settings.DEFAULT_FROM_EMAIL,
        receiver,
        html_message=html_message
    )


def notify_create(event):
    _event_notification(event.host.email, event, 'created')


def notify_delete(event):
    _event_notification(event.host.email, event, 'deleted')


def notify_hide(event):
    _event_notification(event.host.email, event, 'hidden')


def notify_publish(event):
    _event_notification(event.host.email, event, 'published')


def notify_update(event):
    _event_notification(event.host.email, event, 'updated')
