from imagekit import ImageSpec, register
from imagekit.processors import ResizeToFill


class Thumbnail(ImageSpec):
    processors = [ResizeToFill(120, 120)]
    format = 'JPEG'
    options = {'quality': 90}


register.generator('eventary:thumbnail', Thumbnail)


class EventPicture(ImageSpec):
    processors = [ResizeToFill(1024, 350)]
    format = 'JPEG'
    options = {'quality': 90}


register.generator('eventary:eventpicture', EventPicture)
