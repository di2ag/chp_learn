from django.apps import AppConfig


class ChpLearnConfig(AppConfig):
    default = True
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chp_learn'
    label = 'chp_learn'

class ChpLearnDBConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chp_learn.chp_learn'
    label = 'chp_learn'
    verbose_name = 'ChpLearn with ChpDB.'
