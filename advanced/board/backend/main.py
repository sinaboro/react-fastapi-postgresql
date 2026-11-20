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
