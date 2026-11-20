# 8장. 프로젝트 ② FastAPI 회원가입·로그인 API

## 학습 목표

- users 테이블을 만들고 posts 와 외래 키(FK)로 잇는다.
- 회원가입(비밀번호 해시 저장)과 로그인(JWT 발급) API 를 만든다.
- `Depends` 로 "토큰 검사 → 현재 사용자" 의존성을 만들어 여러 API 에 붙인다.
- 글쓴이 본인만 수정·삭제하도록 403 소유권 검사를 넣는다.
- `/docs` 의 **Authorize** 로 토큰을 넣어 API 를 시험한다.

## 8-1. 무엇이 바뀌나

**데이터베이스** - 사용자 표가 생기고, 글은 작성자 **이름(글자)** 대신 작성자 **번호(user_id)** 를 가진다.

![users 와 posts 의 관계](../images/fig_erd.png)

| | 기초 과정 | 심화 과정 |
|---|---|---|
| 작성자 | 글쓰기 폼에서 아무 이름이나 입력 (`writer`) | 로그인한 사람 (토큰에서 알아냄) |
| 글쓰기 | 누구나 | 로그인한 사람만 (아니면 401) |
| 수정·삭제 | 누구나 | 글쓴이 본인만 (아니면 403) |
| DB | `board` (포트 5433) | `authboard` (포트 5434) |

**API** - 인증 API 3개가 늘고, 글 API 에 로그인 확인이 붙는다.

| 주소 | 방식 | 로그인 | 하는 일 | 성공 |
|---|---|---|---|---|
| `/api/auth/signup` | POST | - | 회원가입 | 201 |
| `/api/auth/login` | POST | - | 로그인 → 토큰 | 200 |
| `/api/auth/me` | GET | 필요 | 토큰 주인 정보 | 200 |
| `/api/posts` | GET | - | 목록 (`?user_id=3` 이면 그 사람 글만) | 200 |
| `/api/posts/{id}` | GET | - | 글 하나 | 200 |
| `/api/posts` | POST | 필요 | 글쓰기 | 201 |
| `/api/posts/{id}` | PUT | 본인 | 수정 | 200 |
| `/api/posts/{id}` | DELETE | 본인 | 삭제 | 204 |

## 8-2. 준비 - DB 켜기

6장에서 `C:\study\authboard` 에 `docker-compose.yml` 과 `backend` 를 복사하고 가상환경까지 만들었다. (안 했다면 6-5 의 명령을 먼저 실행한다.)

<!-- file: advanced/board/docker-compose.yml -->

```yaml
# =====================================================================
# 심화 과정 8~9장 - 로그인 게시판 데이터베이스 (PostgreSQL 18)
#
#   시작        : docker compose up -d        (이 파일이 있는 폴더에서)
#   상태 확인   : docker compose ps           (STATUS 가 healthy 이면 준비 완료)
#   멈추기      : docker compose stop         (데이터는 남는다)
#   완전히 지우기: docker compose down -v      (컨테이너 + 데이터 볼륨 삭제, 되돌릴 수 없음)
#
# 접속 정보
#   호스트 localhost / 포트 5434 / DB authboard / 사용자 postgres / 비밀번호 postgres
#   ※ 기초 과정 DB(5433, react-board-db)와 따로 쓴다. 테이블 구조(users 추가)가 달라서
#     기초 과정 글과 섞이지 않게 하려는 것. 두 DB 를 동시에 켜 두어도 포트가 달라 괜찮다.
# =====================================================================

# 프로젝트 이름. 적지 않으면 "폴더 이름"(board)이 프로젝트 이름이 되는데,
# 기초·심화 두 과정의 폴더 이름이 모두 board 라서 서로를 같은 프로젝트로 보고
# 한쪽을 켜면 다른 쪽 컨테이너를 지워 버린다. 이름을 따로 붙여 이 문제를 막는다.
name: react-auth-board

services:
  db:
    image: postgres:18
    container_name: react-auth-db
    restart: unless-stopped
    ports:
      - "5434:5432"                   # 내 PC 5434 → 컨테이너 5432
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres     # 실습용 비밀번호
      POSTGRES_DB: authboard
      TZ: Asia/Seoul
    command: ["postgres", "-c", "timezone=Asia/Seoul"]
    volumes:
      - authboard_data:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d authboard"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  authboard_data:
```

**[PS]**

```powershell
cd C:\study\authboard
docker compose up -d
docker compose ps
```

`react-auth-db` 가 `(healthy)` 이면 준비 끝. 기초 과정 DB(react-board-db, 5433)와 **동시에 켜 두어도** 포트와 프로젝트 이름이 달라 괜찮다.

<!-- file: advanced/board/backend/requirements.txt -->

```text
# Advanced course board API with login (install: pip install -r requirements.txt)
# NOTE: keep this file ASCII-only. pip on Korean Windows may fail to read non-ASCII text.
fastapi==0.162.2            # web API framework
uvicorn[standard]==0.54.0   # server that runs FastAPI
psycopg[binary]==3.3.8      # PostgreSQL driver
PyJWT==2.15.1               # JWT login token (new in advanced course)
pwdlib[argon2]==0.4.2       # password hashing with Argon2 (new in advanced course)
```

## 8-3. security.py - 해시와 토큰 도구

6장에서 실험한 두 가지를 서버에서 쓰기 좋게 함수로 만든다.

<!-- file: advanced/board/backend/security.py -->

```python
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
```

> **SECRET_KEY 는 비밀이다.** 이 값을 아는 사람은 누구의 토큰이든 만들 수 있다. 실제 서비스에서는 코드에 적지 않고 환경 변수로 넣으며, GitHub 에 올리지 않는다. 주석의 명령으로 무작위 값을 만들 수 있다.

## 8-4. db.py - users 테이블과 JOIN

<!-- file: advanced/board/backend/db.py -->

```python
"""db.py - PostgreSQL 에 SQL 을 보내는 함수 모음 (users + posts 두 테이블)

기초 과정 db.py 와 달라진 점
  - users 테이블이 생겼다 (아이디, 비밀번호 해시, 닉네임)
  - posts 에 writer(작성자 이름 글자) 대신 user_id(누가 썼는지 번호)가 들어간다.
      posts.user_id → users.id  를 가리키는 외래 키(FOREIGN KEY)
      → 없는 사용자 번호로는 글을 쓸 수 없고, 사용자를 지우면 그 사람 글도 함께 지워진다(ON DELETE CASCADE)
  - 글을 읽을 때 users 와 JOIN 해서 작성자 닉네임(writer)을 함께 돌려준다.
  - 수정·삭제 SQL 에 "AND user_id = %s" 는 넣지 않았다. 소유권 검사는 main.py 에서 먼저 하고
    403(권한 없음)과 404(없는 글)를 구분해서 알려 주기 위해서다.
"""
import os

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/authboard")


def connect():
    """DB 연결 하나. with 블록이 끝나면 자동 commit(오류면 rollback) 후 닫힌다."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    """테이블이 없으면 만든다 (서버 시작 때 한 번)."""
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id             SERIAL PRIMARY KEY,
                username       VARCHAR(30)  NOT NULL UNIQUE,      -- 로그인 아이디 (중복 불가)
                password_hash  VARCHAR(255) NOT NULL,             -- 비밀번호가 아니라 "해시" 를 저장
                nickname       VARCHAR(30)  NOT NULL,             -- 화면에 보일 이름
                created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id          SERIAL PRIMARY KEY,
                user_id     INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- 쓴 사람
                title       VARCHAR(100) NOT NULL,
                content     TEXT         NOT NULL DEFAULT '',
                created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
                updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
            )
            """
        )


# ================================================================== users
def create_user(username, password_hash, nickname):
    """회원 저장. 아이디가 이미 있으면 None (UNIQUE 위반을 잡아서)."""
    try:
        with connect() as conn:
            return conn.execute(
                """
                INSERT INTO users (username, password_hash, nickname) VALUES (%s, %s, %s)
                RETURNING id, username, nickname
                """,
                (username, password_hash, nickname),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        return None


def get_user_by_username(username):
    """로그인할 때: 아이디로 회원 찾기 (비밀번호 해시 포함)."""
    with connect() as conn:
        return conn.execute(
            "SELECT id, username, nickname, password_hash FROM users WHERE username = %s", (username,)
        ).fetchone()


def get_user(user_id):
    """토큰 검사 후: 번호로 회원 찾기 (비밀번호 해시는 꺼내지 않는다)."""
    with connect() as conn:
        return conn.execute("SELECT id, username, nickname FROM users WHERE id = %s", (user_id,)).fetchone()


# ================================================================== posts
# 글과 작성자 닉네임을 함께 꺼내는 SELECT. u.nickname 을 writer 라는 이름으로 돌려준다
#   → 기초 과정 화면에서 쓰던 post.writer 를 그대로 쓸 수 있다
POST_SELECT = """
    SELECT p.id, p.user_id, u.nickname AS writer, p.title, p.content, p.created_at, p.updated_at
      FROM posts p
      JOIN users u ON u.id = p.user_id
"""


def list_posts(user_id=None):
    """글 목록. user_id 를 주면 그 사람 글만 ("내 글" 보기)."""
    with connect() as conn:
        if user_id is None:
            return conn.execute(POST_SELECT + " ORDER BY p.id DESC").fetchall()
        return conn.execute(POST_SELECT + " WHERE p.user_id = %s ORDER BY p.id DESC", (user_id,)).fetchall()


def get_post(post_id):
    with connect() as conn:
        return conn.execute(POST_SELECT + " WHERE p.id = %s", (post_id,)).fetchone()


def create_post(user_id, title, content):
    """새 글 저장 후, 닉네임까지 붙은 모양으로 다시 읽어 돌려준다."""
    with connect() as conn:
        new_id = conn.execute(
            "INSERT INTO posts (user_id, title, content) VALUES (%s, %s, %s) RETURNING id",
            (user_id, title, content),
        ).fetchone()["id"]
    return get_post(new_id)  # with 블록이 끝나 commit 된 뒤에 읽는다


def update_post(post_id, title, content):
    with connect() as conn:
        conn.execute(
            "UPDATE posts SET title = %s, content = %s, updated_at = now() WHERE id = %s",
            (title, content, post_id),
        )
    return get_post(post_id)


def delete_post(post_id):
    with connect() as conn:
        conn.execute("DELETE FROM posts WHERE id = %s", (post_id,))
```

- `REFERENCES users(id) ON DELETE CASCADE` - posts.user_id 는 반드시 users 에 있는 번호여야 하고, 사용자가 지워지면 그 사람 글도 함께 지워진다.
- `JOIN users u ON u.id = p.user_id` 로 닉네임을 붙여 `writer` 라는 이름으로 돌려준다. 그래서 React 쪽 `post.writer` 코드를 거의 고치지 않아도 된다.
- 아이디가 겹치면 PostgreSQL 이 `UNIQUE` 위반 오류를 낸다. `create_user` 가 이를 잡아 `None` 을 돌려주고, main.py 가 **409** 로 바꾼다.

## 8-5. main.py - 인증 API 와 소유권 검사

<!-- file: advanced/board/backend/main.py -->

```python
"""main.py - 로그인 게시판 REST API 서버 (FastAPI + JWT)

기초 과정 main.py 에 더해진 것
  - 회원가입 / 로그인 / 내 정보 API
  - get_current_user : 요청 헤더의 토큰을 검사해 "지금 요청한 사람" 을 알아내는 의존성(Depends)
  - 글쓰기·수정·삭제는 로그인한 사람만 (토큰이 없거나 틀리면 401)
  - 수정·삭제는 글쓴이 본인만 (남의 글이면 403)

  주소                       방식     로그인   하는 일
  /api/auth/signup           POST     -        회원가입 (201)
  /api/auth/login            POST     -        로그인 → 토큰 발급
  /api/auth/me               GET      필요     토큰 주인의 정보
  /api/posts                 GET      -        글 목록 (?user_id=3 이면 그 사람 글만)
  /api/posts/{post_id}       GET      -        글 하나
  /api/posts                 POST     필요     새 글 (작성자 = 토큰 주인)
  /api/posts/{post_id}       PUT      본인     글 수정
  /api/posts/{post_id}       DELETE   본인     글 삭제 (204)

  상태 코드 정리
    401 Unauthorized : "누구세요?" - 로그인 안 했거나 토큰이 만료/위조됨 → 다시 로그인해야 함
    403 Forbidden    : "당신은 알지만 안 됩니다" - 로그인은 했지만 남의 글
    404 Not Found    : 그런 글 없음
    409 Conflict     : 이미 있는 아이디로 가입

실행: uvicorn main:app --reload   (backend 폴더, 가상환경 켠 상태)  →  http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

import db
import security


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="React 게시판 API (심화: 로그인)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],  # Authorization 헤더도 허락해야 토큰을 보낼 수 있다
)


# ================================================================== 데이터 모양
class SignupIn(BaseModel):
    # pattern: 영문 소문자·숫자·밑줄만 4~20자 (정규 표현식)
    username: str = Field(min_length=4, max_length=20, pattern=r"^[a-z0-9_]+$")
    password: str = Field(min_length=8, max_length=72)
    nickname: str = Field(min_length=1, max_length=30)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    nickname: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut  # 로그인하자마자 화면에 닉네임을 보여 줄 수 있게 함께 돌려준다


class PostIn(BaseModel):
    # 작성자(writer)는 더 이상 입력받지 않는다 → 토큰 주인이 작성자. (남의 이름으로 글쓰기 불가)
    title: str = Field(min_length=1, max_length=100)
    content: str = ""


class PostOut(BaseModel):
    id: int
    user_id: int
    writer: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


# ================================================================== 로그인 확인 (의존성)
# HTTPBearer: 요청 헤더 "Authorization: Bearer <토큰>" 에서 토큰을 꺼내 준다.
#   auto_error=False → 헤더가 없어도 FastAPI 가 바로 오류를 내지 않고 None 을 준다
#   (아래에서 우리가 고른 한국어 401 메시지를 돌려주려고)
bearer = HTTPBearer(auto_error=False)


def get_current_user(cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    """토큰을 검사해 사용자(딕셔너리)를 돌려준다. 문제가 있으면 401.

    API 함수의 매개변수에 user: CurrentUser 라고 쓰기만 하면,
    FastAPI 가 그 함수보다 "먼저" 이 함수를 실행해 결과를 넣어 준다. (의존성 주입)
    """
    if cred is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    user_id = security.decode_access_token(cred.credentials)
    user = db.get_user(user_id) if user_id else None  # 탈퇴 등으로 사용자가 없어졌을 수도 있다
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 만료되었습니다. 다시 로그인하세요")
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]  # 자주 쓰므로 짧은 이름을 붙여 둔다


def find_post_or_404(post_id: int):
    post = db.get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다")
    return post


def check_owner(post: dict, user: dict):
    """글쓴이 본인이 아니면 403."""
    if post["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="본인이 쓴 글만 수정·삭제할 수 있습니다")


# ================================================================== 인증 API
@app.post("/api/auth/signup", response_model=UserOut, status_code=201)
def signup(body: SignupIn):
    hashed = security.hash_password(body.password)  # 비밀번호 → 해시 (원래 비밀번호는 저장하지 않는다)
    user = db.create_user(body.username, hashed, body.nickname.strip())
    if user is None:
        raise HTTPException(status_code=409, detail="이미 사용 중인 아이디입니다")
    return user


@app.post("/api/auth/login", response_model=TokenOut)
def login(body: LoginIn):
    user = db.get_user_by_username(body.username)
    # 아이디가 없을 때와 비밀번호가 틀릴 때 같은 메시지를 준다
    #   → "이 아이디는 있다" 는 정보를 공격자에게 주지 않기 위해
    if user is None or not security.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다")
    token = security.create_access_token(user["id"])
    return {"access_token": token, "user": user}  # user 의 password_hash 는 UserOut 모양에 없어서 빠진다


@app.get("/api/auth/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


# ================================================================== 게시글 API
@app.get("/api/posts", response_model=list[PostOut])
def list_posts(user_id: int | None = None):  # 주소 뒤 ?user_id=3 (쿼리 매개변수, 없어도 됨)
    return db.list_posts(user_id)


@app.get("/api/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int):
    return find_post_or_404(post_id)


@app.post("/api/posts", response_model=PostOut, status_code=201)
def create_post(body: PostIn, user: CurrentUser):  # user: 로그인 확인을 통과해야 이 함수가 실행된다
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="제목을 입력하세요")
    return db.create_post(user["id"], title, body.content.strip())


@app.put("/api/posts/{post_id}", response_model=PostOut)
def update_post(post_id: int, body: PostIn, user: CurrentUser):
    post = find_post_or_404(post_id)  # 1. 글이 있나? (없으면 404)
    check_owner(post, user)           # 2. 내 글인가? (아니면 403)
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="제목을 입력하세요")
    return db.update_post(post_id, title, body.content.strip())


@app.delete("/api/posts/{post_id}", status_code=204)
def delete_post(post_id: int, user: CurrentUser):
    post = find_post_or_404(post_id)
    check_owner(post, user)
    db.delete_post(post_id)
    return Response(status_code=204)
```

**의존성 주입(Depends) 읽는 법**

```python
CurrentUser = Annotated[dict, Depends(get_current_user)]

@app.post("/api/posts")
def create_post(body: PostIn, user: CurrentUser): ...
```

1. 요청이 오면 FastAPI 는 `create_post` 를 실행하기 **전에** `get_current_user` 를 먼저 실행한다.
2. `get_current_user` 는 `bearer`(HTTPBearer)에게 헤더의 토큰을 받아 검사한다. 문제가 있으면 여기서 401 을 던지고 끝난다. `create_post` 는 실행조차 되지 않는다.
3. 통과하면 돌려준 사용자 딕셔너리가 `user` 매개변수로 들어간다.

로그인이 필요한 API 에는 `user: CurrentUser` 한 줄만 붙이면 된다.

**403 과 404 의 순서** `update_post` 는 ① 글이 있는지(404) → ② 내 글인지(403) 순서로 검사한다. SQL 에 `WHERE id = %s AND user_id = %s` 를 넣는 방법도 있지만, 그러면 "없는 글" 과 "남의 글" 을 구분할 수 없어 화면에 정확한 이유를 보여 주기 어렵다.

**로그인 실패 메시지를 하나로** 아이디가 없을 때와 비밀번호가 틀릴 때 같은 문구("아이디 또는 비밀번호가 올바르지 않습니다")를 돌려준다. 다르게 알려 주면 공격자가 "이 아이디는 가입되어 있구나" 를 알아낼 수 있다.

## 8-6. 서버 실행과 /docs 로 시험하기

**[PS]** `C:\study\authboard\backend`, `(.venv)` 가 켜진 터미널

```powershell
uvicorn main:app --reload
```

> 기초 과정 API 서버가 아직 8000 번에서 돌고 있다면 먼저 그 터미널에서 **Ctrl+C** 로 끈다. 같은 포트를 두 서버가 쓸 수 없다.

http://localhost:8000/docs 를 연다. 자물쇠 🔒 가 붙은 API 가 로그인이 필요한 API 다.

![로그인 API 가 추가된 /docs](../images/a8_docs.png)

**순서대로 시험하기**

1. **POST /api/auth/signup** → Try it out → 아래 본문으로 Execute → **201**

```json
{ "username": "minsu", "password": "password123", "nickname": "민수" }
```

2. 같은 본문으로 한 번 더 → **409** `"이미 사용 중인 아이디입니다"`
3. **POST /api/auth/login** → `{"username": "minsu", "password": "password123"}` → **200**. 응답의 `access_token` 값(따옴표 안)을 복사한다.

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwia...",
  "token_type": "bearer",
  "user": { "id": 1, "username": "minsu", "nickname": "민수" }
}
```

4. **POST /api/posts** 를 토큰 없이 Execute → **401** `"로그인이 필요합니다"`
5. 오른쪽 위 **Authorize** 버튼 → Value 칸에 복사한 토큰을 붙여 넣고(앞에 Bearer 는 쓰지 않는다) → Authorize → Close
6. 다시 **POST /api/posts** → `{"title": "민수의 첫 글", "content": "hi"}` → **201**. `writer` 가 `"민수"` 로 들어가 있다.
7. 회원을 하나 더 만들고(`jisu`) 그 토큰으로 Authorize 를 바꾼 뒤, 민수의 글을 **PUT** 또는 **DELETE** → **403** `"본인이 쓴 글만 수정·삭제할 수 있습니다"`

교안을 만들 때 같은 시험을 자동으로 돌린 실제 결과다.

```text
signup 201 {'id': 1, 'username': 'minsu', 'nickname': '민수'}
dup 409 {'detail': '이미 사용 중인 아이디입니다'}
wrongpw 401 {'detail': '아이디 또는 비밀번호가 올바르지 않습니다'}
me 200 {'id': 1, 'username': 'minsu', 'nickname': '민수'}
noauth post 401 {'detail': '로그인이 필요합니다'}
bad token 401 {'detail': '로그인이 만료되었습니다. 다시 로그인하세요'}
create 201 {'id': 1, 'user_id': 1, 'writer': '민수', 'title': '민수의 글', ...}
other put 403 {'detail': '본인이 쓴 글만 수정·삭제할 수 있습니다'}
own put 200 {'id': 1, 'user_id': 1, 'writer': '민수', 'title': '수정', ...}
other del 403 {'detail': '본인이 쓴 글만 수정·삭제할 수 있습니다'}
own del 204
404 404 {'detail': '글을 찾을 수 없습니다'}
expired 401 {'detail': '로그인이 만료되었습니다. 다시 로그인하세요'}
```

**DB 에서 확인하기** - 비밀번호가 아니라 해시가 저장되어 있다.

**[PS]**

```powershell
docker exec react-auth-db psql -U postgres -d authboard -c "SELECT id, username, left(password_hash, 40) AS password_hash, nickname FROM users;"
```

```text
 id | username |              password_hash               | nickname
----+----------+------------------------------------------+----------
  1 | jisu     | $argon2id$v=19$m=65536,t=3,p=4$KH3G8QI+p | 지수
  3 | minsu    | $argon2id$v=19$m=65536,t=3,p=4$+laxpGAXB | 민수
(2 rows)
```

> 위 결과에서 번호가 1, 3 으로 2 가 비어 있다. 이미 있는 아이디로 가입을 시도하면 INSERT 가 실패하는데, 그때도 SERIAL 번호(시퀀스)는 하나 소모되기 때문이다. 번호는 "고유하기만 하면 되는 값" 이라 빈 번호가 있어도 문제없다.

## 정리

- users(아이디 UNIQUE, 비밀번호 **해시**, 닉네임) 1 : N posts(user_id FK).
- 가입: 해시해서 저장, 중복이면 409. 로그인: 해시 비교 → JWT 발급.
- `user: CurrentUser` (Depends) 한 줄로 "로그인 필수 + 현재 사용자" 를 얻는다.
- 수정·삭제: 404(없음) → 403(남의 글) 순서로 검사.
- 작성자는 입력받지 않고 토큰에서 정한다 → 남의 이름으로 쓸 수 없다.

## 확인 문제

1. `get_current_user` 가 401 을 던지는 경우를 세 가지 쓰시오.
2. 글쓰기 요청 본문에 `"user_id": 99` 를 넣어 보내면 99번 사용자의 글로 저장되는가? 코드를 근거로 답하시오.
3. 비밀번호를 8자 미만으로 가입 요청하면 몇 번 상태 코드가 오는가? 그 검사는 어느 코드가 하는가?
4. `/api/auth/me` 에 회원의 가입 날짜(`created_at`)도 함께 돌려주려면 어느 파일의 어디를 고쳐야 하는지 모두 쓰시오.
5. `SECRET_KEY` 를 바꾸고 서버를 다시 켜면, 이미 로그인해 있던 사용자들은 어떻게 되는가?
