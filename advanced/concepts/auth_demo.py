"""auth_demo.py - 6장 인증 개념을 눈으로 확인하는 실습 (서버·DB 없이 실행)

이 예제가 보여 주는 것
  1. 같은 비밀번호도 해시할 때마다 결과가 다르다 (소금 salt 때문). 그래도 검사는 통과한다.
  2. JWT 는 점(.)으로 나뉜 세 부분(헤더.내용.서명)이고, 내용은 누구나 읽을 수 있다.
  3. 내용을 한 글자라도 고치면 서명이 맞지 않아 서버가 거절한다 (위조 방지).
  4. 만료 시각(exp)이 지난 토큰도 거절된다.

실행 (advanced/board/backend 의 가상환경을 켠 상태에서, 이 파일이 있는 폴더에서)
  python auth_demo.py
"""
import base64
import json
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

SECRET = "demo-secret-key-for-class-0123456789"  # 실습용 비밀 열쇠

# ------------------------------------------------------------------ 1. 비밀번호 해시
print("=== 1. 비밀번호 해시 ===")
ph = PasswordHash.recommended()
h1 = ph.hash("password123")
h2 = ph.hash("password123")
print("해시 1:", h1[:60] + "...")
print("해시 2:", h2[:60] + "...")
print("두 해시가 같은가?", h1 == h2)                      # False - 소금이 달라서
print("맞는 비밀번호 검사:", ph.verify("password123", h1))  # True
print("틀린 비밀번호 검사:", ph.verify("password124", h1))  # False

# ------------------------------------------------------------------ 2. JWT 만들기와 읽기
print("\n=== 2. JWT 구조 ===")
now = datetime.now(timezone.utc)
token = jwt.encode({"sub": "1", "exp": now + timedelta(minutes=60)}, SECRET, algorithm="HS256")
header, payload, signature = token.split(".")
print("토큰:", token[:50] + "...")
print("부분 개수:", len(token.split(".")))


def b64decode(part):
    """JWT 는 base64url 로 인코딩되어 있다. 빠진 = 를 채워 디코딩 → 누구나 내용을 볼 수 있다."""
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


print("헤더 내용:", b64decode(header))
print("본문 내용:", {k: v for k, v in b64decode(payload).items() if k != "exp"}, "+ exp(만료 시각)")
print("서명 검사 후 꺼낸 sub:", jwt.decode(token, SECRET, algorithms=["HS256"])["sub"])

# ------------------------------------------------------------------ 3. 위조하면?
print("\n=== 3. 내용을 고친 토큰 ===")
fake_body = base64.urlsafe_b64encode(json.dumps({"sub": "2", "exp": 9999999999}).encode()).decode().rstrip("=")
fake = f"{header}.{fake_body}.{signature}"  # 2번 사용자로 바꿔치기, 서명은 원래 것 그대로
try:
    jwt.decode(fake, SECRET, algorithms=["HS256"])
except jwt.InvalidSignatureError as e:
    print("거절:", type(e).__name__)

# ------------------------------------------------------------------ 4. 만료된 토큰
print("\n=== 4. 만료된 토큰 ===")
old = jwt.encode({"sub": "1", "exp": now - timedelta(seconds=1)}, SECRET, algorithm="HS256")
try:
    jwt.decode(old, SECRET, algorithms=["HS256"])
except jwt.ExpiredSignatureError as e:
    print("거절:", type(e).__name__)
