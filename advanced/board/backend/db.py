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
