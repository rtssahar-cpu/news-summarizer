from django.test import SimpleTestCase


class SmokeTestCase(SimpleTestCase):
    def test_settings_loaded(self):
        from django.conf import settings

        self.assertTrue(settings.configured)
