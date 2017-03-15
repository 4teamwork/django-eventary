import os
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf', '.png', '.jpg']
    if not ext.lower() in valid_extensions:
        raise ValidationError(_('Unsupported file extension'))


def validate_image_extension(value):
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.png', '.jpg']
    if not ext.lower() in valid_extensions:
        raise ValidationError(_('Unsupported image extension'))
