# helper functions for file operations
import os

mime_types = {
    'csv': 'text/csv',
    'json': 'application/json',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'pdf': 'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}


def get_mime_type(file_path):
    ext = file_path.split('.')[-1]
    return mime_types.get(ext, 'text/plain')

def is_file_allowed(file_path):
    allowed_extensions = list(mime_types.keys())
    ext = file_path.split('.')[-1]
    return ext in allowed_extensions

def upload_file(file, name):
    upload_path = os.path.join('static','uploads')
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)
    # uncomment the below line to restrict file types
    # if not is_file_allowed(name):
    #     return None
    file_path = os.path.join(upload_path, name)
    file.save(file_path)
    return file_path