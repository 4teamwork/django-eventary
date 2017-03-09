from imagekit import ImageSpec, register
from imagekit.processors import ResizeToFill


class Thumbnail(ImageSpec):
    processors = [ResizeToFill(160, 160)]
    format = 'JPEG'
    options = {'quality': 90}


register.generator('eventary:thumbnail', Thumbnail)
