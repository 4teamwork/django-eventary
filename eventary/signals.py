from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Event


# alerts of newly saved event
@receiver(post_save, sender=Event)
def save_event(sender, instance, **kwargs):
    # send mail to winterthur and organizer with status on every change
    #send_mail(
    #    'This is my subject',
    #    'Here is my message. I have nothing to say',
    #    'noreply@mylocalhost.com',
    #    ['pablo.verges@gmail.com'],
    #    fail_silently=False
    #)
    #print("this should send an email?")
    pass
