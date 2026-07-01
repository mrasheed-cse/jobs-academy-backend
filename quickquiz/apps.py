from django.apps import AppConfig


class QuickquizConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quickquiz'

    def ready(self):
        import quickquiz.signals