"""Keep module ownership and native Drawer/Tabs contracts reviewable."""
import ast
import re
from pathlib import Path
from django.test import SimpleTestCase

ROOT=Path(__file__).resolve().parents[5]
BACKEND=ROOT/'src/backend/lims'
WEB=ROOT/'src/web/src/views/lims'
PAGES=('costing/costType','costing/costItem','costing/costPackage','catalog/service','catalog/product','catalog/scheme','customer/customer','customer/contact','commercial/quotation','commercial/contract')

class OwnershipTests(SimpleTestCase):
    def test_generic_backend_has_no_concrete_business_imports(self):
        for path in (BACKEND/'shared').glob('*.py'):
            tree=ast.parse(path.read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                names=[node.module or ''] if isinstance(node,ast.ImportFrom) else [n.name for n in node.names] if isinstance(node,ast.Import) else []
                for name in names:self.assertFalse(name.startswith(('lims.costing','lims.catalog','lims.customer','lims.commercial')),str(path)+':'+name)
        for app in ('costing','catalog','customer','commercial'):
            self.assertTrue((BACKEND/app/'access_contract.py').is_file())

    def test_registry_only_aggregates_metadata(self):
        tree=ast.parse((BACKEND/'access_registry.py').read_text())
        self.assertFalse(any(isinstance(n,(ast.If,ast.FunctionDef,ast.ClassDef)) for n in ast.walk(tree)))

    def test_frontend_pages_own_apis_and_crud(self):
        for file in ('api.ts','crud.tsx','m2Api.ts','m2Crud.tsx','CompositionEditor.vue'):
            self.assertFalse((WEB/'shared'/file).exists())
        for page in PAGES:
            api=(WEB/page/'api.ts').read_text(encoding='utf-8')
            crud=(WEB/page/'crud.tsx').read_text(encoding='utf-8')
            self.assertIn("/@/utils/service",api)
            for method in ('list:', 'retrieve:', 'field_permission:', 'create:', 'update:', 'destroy:'):self.assertIn(method,api)
            self.assertIn('columns:',crud);self.assertIn('request:',crud)
            self.assertIn("is:'el-drawer'",re.sub(r'\s+', '', crud))
            for factory in ('apiFor(', 'makeCrud(', 'm2Api(', 'makeM2Crud('):self.assertNotIn(factory,api+crud)
        for path in WEB.rglob('*'):
            if path.suffix not in ('.vue','.ts','.tsx'):continue
            text=path.read_text(encoding='utf-8')
            for legacy in ('shared/m2Api','shared/m2Crud','shared/crud','shared/api'):
                self.assertNotIn(legacy,text,str(path))

    def test_complex_native_tabs_and_local_editors(self):
        for page in ('costing/costPackage','catalog/service','catalog/product','catalog/scheme','commercial/quotation','commercial/contract'):
            text=(WEB/page/'crud.tsx').read_text(encoding='utf-8')
            self.assertIn("groupType:'tabs'",re.sub(r'\s+', '', text))
        for path in (WEB/'shared').glob('*'):
            text=path.read_text(encoding='utf-8')
            self.assertNotIn('props.resource',text)
            self.assertNotIn('props.kind',text)
        for path in WEB.rglob('*Editor.vue'):
            self.assertNotIn('props.kind',path.read_text(encoding='utf-8'))

    def test_contact_api_and_snapshot_breaking_contract(self):
        from lims.customer.access_contract import READ,WRITE
        from lims.commercial.access_contract import SNAPSHOT
        self.assertNotIn('contacts',READ['customer'].split())
        self.assertNotIn('contacts',WRITE['customer'].split())
        for key in ('phone','department','remark'):self.assertNotIn(key,READ['contact'].split())
        self.assertIn('contact_mobile_snapshot',SNAPSHOT)
        self.assertNotIn('contact_phone_snapshot',SNAPSHOT)
