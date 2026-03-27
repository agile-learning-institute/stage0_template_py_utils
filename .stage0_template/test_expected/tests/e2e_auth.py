"""Static bearer JWT for E2E tests against the demo server.

Must match ``JWT_SECRET`` used when running the API locally. The template ``pipenv run dev`` script
sets ``JWT_SECRET=mentorhub-local-dev-jwt-secret-fixed``. Claims: iss ``dev-idp``, aud ``dev-api``;
subject ``adam`` with role ``admin``.
"""

E2E_ACCESS_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkZXYtaWRwIiwiYXVkIjoiZGV2LWFwaSIsInN1YiI6ImFkYW0iLCJpYXQiOjE3NzQ1NTMwNTEsImV4cCI6MjA4OTkxMzA1MSwicm9sZXMiOlsiYWRtaW4iXX0.JqJywkxLUoOvbE5SAzEdV3Ia87vDZCuDZXTGFYfmY7c"
)


def get_auth_token() -> str:
    return E2E_ACCESS_TOKEN
