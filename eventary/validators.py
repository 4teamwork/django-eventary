import os

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


def validate_image_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.jpg', '.png']
    if not ext.lower() in valid_extensions:
        raise ValidationError(_('Unsupported image format.'))


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.jpg', '.png']
    if not ext.lower() in valid_extensions:
        raise ValidationError(_('Unsupported file extension.'))
