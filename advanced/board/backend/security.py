"""security.py - 비밀번호 해시와 JWT 토큰 (로그인의 핵심 도구 두 가지)

이 파일이 보여 주는 것
  1. 비밀번호는 절대 그대로 저장하지 않는다 → "해시" 로 바꿔 저장한다.
     - 해시: 한쪽 방향으로만 바뀌는 변환. 해시값으로 원래 비밀번호를 알아낼 수 없다.
     - 로그인할 때는 입력한 비밀번호를 같은 방식으로 바꿔 저장된 해시와 "비교" 만 한다.
     - Argon2 는 일부러 느리고 매번 다른 소금(salt)을 섞어서, 같은 비밀번호도 해시가 매번 다르다.
  2. 로그인에 성공하면 JWT(JSON Web Token) 를 발급한다.
     - 토큰 안에 "누구인지(sub)" 와 "언제까지 유효한지(exp)" 를 적고 SECRET_KEY 로 서명한다.
     - 서버는 토큰을 따로 저장하지 않는다. 서명만 검사하면 위조 여부를 알 수 있다.
     - 토큰 내용은 누구나 읽을 수 있다(암호화가 아님). 그래서 비밀번호 같은 것은 넣지 않는다.
"""
import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

# ------------------------------------------------------------------ 설정
# SECRET_KEY: 토큰 서명에 쓰는 비밀 열쇠. 이 값이 새면 누구나 토큰을 위조할 수 있다.
#   실제 서비스에서는 환경 변수로 넣고 코드에 적지 않는다. (실습이라 기본값을 둔다)
#   만들기: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me-0123456789abcdef")
ALGORITHM = "HS256"                                   # 서명 방식 (비밀 열쇠 하나로 서명·검사)
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))  # 토큰 유효 시간(분)

password_hash = PasswordHash.recommended()            # 권장 설정의 Argon2


# ------------------------------------------------------------------ 비밀번호
def hash_password(plain: str) -> str:
    """'secret123' → '$argon2id$v=19$m=65536,...' 같은 해시 문자열"""
    return password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """입력한 비밀번호가 저장된 해시와 맞는지 검사 (맞으면 True)"""
    return password_hash.verify(plain, hashed)


# ------------------------------------------------------------------ JWT
def create_access_token(user_id: int) -> str:
    """사용자 번호를 담은 토큰을 만든다."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),                          # subject: 이 토큰의 주인 (문자열로 넣는 것이 규칙)
        "iat": now,                                   # issued at: 발급 시각
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),  # expiration: 만료 시각
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """토큰을 검사해 사용자 번호를 돌려준다. 위조됐거나 만료됐으면 None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # 서명·만료를 함께 검사
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        # ExpiredSignatureError(만료), InvalidSignatureError(위조) 등이 모두 InvalidTokenError 의 한 종류
        return None
