"""End-to-end check of the Neon services: Postgres, bucket, Auth."""
import time
import uuid

import httpx

from talent_scout.kernel.settings import ROOT_ENV, Settings
from talent_scout.neon import BUCKET, bucket, pg_connect, verify_token


def main():
    s = Settings()
    with pg_connect(s) as c:
        c.execute("create table if not exists smoke(id serial primary key, note text)")
        c.execute("insert into smoke(note) values ('hi')")
        n = c.execute("select count(*) from smoke").fetchone()[0]
        c.execute("drop table smoke")
    print("postgres ok, rows seen:", n)

    b, key = bucket(s), f"smoke/{uuid.uuid4()}.txt"
    b.put_object(Bucket=BUCKET, Key=key, Body=b"hello")
    assert b.get_object(Bucket=BUCKET, Key=key)["Body"].read() == b"hello"
    b.delete_object(Bucket=BUCKET, Key=key)
    print("bucket ok")

    base = [l.split("=", 1)[1].strip().strip('"') for l in ROOT_ENV.read_text().splitlines() if l.startswith("NEON_AUTH_BASE_URL=")][0]
    email = f"smoke-{int(time.time())}@example.com"
    r = httpx.post(f"{base}/sign-up/email", json={"email": email, "password": "Smoke-Test-123!", "name": "smoke"},
                   headers={"Origin": base})
    print("sign-up", r.status_code)
    r.raise_for_status()
    token = r.headers.get("set-auth-jwt") or httpx.get(f"{base}/token", cookies=r.cookies, headers={"Origin": base}).json()["token"]
    print("auth ok, sub:", verify_token(s, token)["sub"])


main()
