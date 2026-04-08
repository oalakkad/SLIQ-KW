from storages.backends.s3boto3 import S3Boto3Storage

class MediaStorage(S3Boto3Storage):
    location = "media"       # ensures everything goes into /media/
    default_acl = None
    file_overwrite = False   # don’t overwrite existing files
