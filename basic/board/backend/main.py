"""main.py - 게시판 REST API 서버 (FastAPI)

이 파일이 보여 주는 것
  - 주소(URL) + 방식(HTTP 메서드) 하나에 함수 하나를 연결하는 FastAPI 의 기본 구조
  - React(다른 주소 5173)에서 오는 요청을 허락하는 CORS 설정
  - 요청 본문(JSON)을 Pydantic 모델로 검사하기 (제목이 비었으면 422 오류)
  - 없는 글이면 404 오류 돌려주기

  주소                    방식     하는 일       CRUD     성공 상태 코드
  /api/posts              GET      글 목록       Read     200 OK
  /api/posts/{post_id}    GET      글 하나       Read     200 OK
  /api/posts              POST     새 글 저장    Create   201 Created
  /api/posts/{post_id}    PUT      글 수정       Update   200 OK
  /api/posts/{post_id}    DELETE   글 삭제       Delete   204 No Content

실행 (backend 폴더에서, 가상환경을 켠 뒤)
  uvicorn main:app --reload
  → http://localhost:8000/docs 에서 API 를 바로 시험해 볼 수 있다.
"""
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db


# ------------------------------------------------------------------ 서버 시작 준비
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()  # 서버가 켜질 때 한 번: posts 테이블이 없으면 만든다
    yield         # 여기서부터 요청을 받는다


app = FastAPI(title="React 게시판 API (기초)", lifespan=lifespan)

# CORS: 브라우저는 "다른 주소(출처)" 로 보내는 요청을 기본으로 막는다.
#   React 개발 서버 http://localhost:5173  →  API 서버 http://localhost:8000  (포트가 다르면 다른 출처)
#   그래서 API 서버가 "5173 에서 오는 요청은 받아도 된다" 고 응답 헤더로 알려 줘야 한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # 허락할 출처
    allow_methods=["*"],  # GET, POST, PUT, DELETE 모두
    allow_headers=["*"],  # Content-Type 등 모든 헤더
)


# ------------------------------------------------------------------ 주고받을 데이터 모양
class PostIn(BaseModel):
    """글쓰기·수정 때 React 가 보내는 JSON 의 모양. 조건에 안 맞으면 FastAPI 가 422 로 거절한다."""

    title: str = Field(min_length=1, max_length=100)   # 1~100 글자
    writer: str = Field(min_length=1, max_length=30)   # 1~30 글자
    content: str = ""                                  # 비어도 된다


class PostOut(BaseModel):
    """API 가 돌려주는 글 하나의 모양 (/docs 화면에 예시로 보인다)."""

    id: int
    title: str
    writer: str
    content: str
    created_at: datetime
    updated_at: datetime


def clean(post: PostIn):
    """앞뒤 빈칸을 지운 값. 빈칸만 친 제목은 여기서 걸러 400 오류로 돌려준다."""
    title, writer = post.title.strip(), post.writer.strip()
    if not title or not writer:
        raise HTTPException(status_code=400, detail="제목과 작성자를 입력하세요")
    return title, writer, post.content.strip()


# ------------------------------------------------------------------ Read: 목록
@app.get("/api/posts", response_model=list[PostOut])
def list_posts():
    return db.list_posts()  # 딕셔너리 리스트 → FastAPI 가 JSON 배열로 바꿔 보낸다


# ------------------------------------------------------------------ Read: 하나
@app.get("/api/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int):  # 주소의 {post_id} 가 정수로 바뀌어 들어온다
    post = db.get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다")
    return post


# ------------------------------------------------------------------ Create
@app.post("/api/posts", response_model=PostOut, status_code=201)
def create_post(post: PostIn):  # 요청 본문(JSON)이 PostIn 으로 검사되어 들어온다
    return db.create_post(*clean(post))  # *튜플 → 세 값을 인자 세 개로 펼쳐 넘긴다


# ------------------------------------------------------------------ Update
@app.put("/api/posts/{post_id}", response_model=PostOut)
def update_post(post_id: int, post: PostIn):
    updated = db.update_post(post_id, *clean(post))
    if updated is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다")
    return updated


# ------------------------------------------------------------------ Delete
@app.delete("/api/posts/{post_id}", status_code=204)
def delete_post(post_id: int):
    if not db.delete_post(post_id):
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다")
    return Response(status_code=204)  # 204: 성공했지만 돌려줄 내용은 없음
