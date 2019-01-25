from datetime import datetime
from flask_mongoengine import MongoEngine

db = MongoEngine()

class Device(db.Document):
    name = db.StringField(max_length=255, required=True, unique=True)
    last_updated = db.DateTimeField()
    last_triggered = db.DateTimeField()

    def save(self, *args, **kwargs):
        self.last_updated = datetime.now()
        return super(Device, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

    def to_dict(self):
        device_dict = {}
        device_dict['name'] = self.name
        device_dict['last_triggered'] = self.last_triggered.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return device_dict
