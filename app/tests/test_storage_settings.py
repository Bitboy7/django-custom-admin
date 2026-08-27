import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_storage_settings(debug, **overrides):
    env = os.environ.copy()
    env.update(
        {
            'DEBUG': str(debug),
            'SECRET_KEY': 'storage-test-secret',
            'R2_ACCOUNT_ID': 'test-account',
            'R2_ACCESS_KEY_ID': 'test-access-key',
            'R2_SECRET_ACCESS_KEY': 'test-secret-key',
            'R2_BUCKET_NAME': 'test-bucket',
            'R2_ENDPOINT_URL': '',
            'R2_SIGNED_URL_EXPIRE': '900',
        }
    )
    env.update(overrides)
    script = (
        'import json; from app import settings; '
        'default = settings.STORAGES["default"]; '
        'print(json.dumps({"backend": default["BACKEND"], '
        '"options": {key: str(value) for key, value in '
        'default.get("OPTIONS", {}).items()}}))'
    )
    result = subprocess.run(
        [sys.executable, '-c', script],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_debug_true_uses_local_media_storage():
    storage = _load_storage_settings(True)

    assert storage['backend'] == 'django.core.files.storage.FileSystemStorage'
    assert storage['options']['base_url'] == '/media/'
    assert storage['options']['location'].endswith('media')


def test_debug_false_uses_private_cloudflare_r2_storage():
    storage = _load_storage_settings(False)

    assert storage['backend'] == 'storages.backends.s3.S3Storage'
    assert storage['options']['bucket_name'] == 'test-bucket'
    assert storage['options']['endpoint_url'] == (
        'https://test-account.r2.cloudflarestorage.com'
    )
    assert storage['options']['querystring_auth'] == 'True'
    assert storage['options']['querystring_expire'] == '900'


def test_debug_false_requires_r2_credentials():
    env = os.environ.copy()
    env.update(
        {
            'DEBUG': 'False',
            'SECRET_KEY': 'storage-test-secret',
            'R2_ACCOUNT_ID': '',
            'R2_ACCESS_KEY_ID': '',
            'R2_SECRET_ACCESS_KEY': '',
            'R2_BUCKET_NAME': '',
            'R2_ENDPOINT_URL': '',
        }
    )
    result = subprocess.run(
        [sys.executable, '-c', 'from app import settings'],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert 'Cloudflare R2 es obligatorio cuando DEBUG=False' in result.stderr
