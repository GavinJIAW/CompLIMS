"""Plain text contract: API preserves strings; current consumers must escape."""
from pathlib import Path
from django.test import TestCase, SimpleTestCase
from rest_framework.test import APIClient
from coreadmin.system.models import Users, MessageCenter, MessageCenterTargetUser

PAYLOADS = ('<script>window.__B1D_XSS__=1</script>', '<img src=x onerror="window.__B1D_XSS__=2">', '<b>B1D text</b>')
WEB = Path(__file__).resolve().parents[3] / 'web' / 'src'


class MessageContentTests(TestCase):
    def test_api_preserves_untrusted_string_without_rewriting_history(self):
        user = Users.objects.create(username='message-reader', password='!', is_superuser=True, pwd_change_count=1)
        client = APIClient()
        client.force_authenticate(user)
        for content in PAYLOADS:
            response = client.post('/api/system/message_center/', {'title': 'Plain text', 'content': content, 'target_type': 0, 'target_user': [user.pk]}, format='json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['code'], 2000)
            row = MessageCenter.objects.get(pk=response.data['data']['id'])
            self.assertEqual(row.content, content)
            for path in (f'/api/system/message_center/{row.pk}/', '/api/system/message_center/get_newest_msg/'):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['data']['content'], content)
            row.refresh_from_db()
            self.assertEqual(row.content, content)


class MessageConsumerTests(SimpleTestCase):
    def test_notification_is_text_not_html(self):
        source = (WEB / 'layout/navBars/breadcrumb/userNews.vue').read_text(encoding='utf-8')
        self.assertNotIn('v-html', source)
        self.assertIn('{{ v.content }}', source)
        for sink in ('innerHTML', 'insertAdjacentHTML', 'DOMParser'):
            self.assertNotIn(sink, source)

    def test_form_uses_plain_textarea_and_keeps_edit_disabled(self):
        source = (WEB / 'views/system/messageCenter/crud.tsx').read_text(encoding='utf-8')
        self.assertNotIn('editor-wang5', source)
        self.assertIn("'textarea'", source)
        for sink in ('v-html', 'innerHTML', 'insertAdjacentHTML', 'DOMParser'):
            self.assertNotIn(sink, source)
