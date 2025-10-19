from constants import MIME_TYPES
import os

def get_content_type(filename):
    _, ext = os.path.splitext(filename)
    return MIME_TYPES.get(ext, 'application/octet-stream')