"""db.py - PostgreSQL 에 SQL 을 보내는 함수 모음 (게시판 posts 테이블)

이 파일이 보여 주는 것
  - psycopg 로 DB 에 접속해 SQL 을 실행하는 방법
  - 함수 하나 = SQL 하나. main.py(API) 는 이 함수들만 부르고 SQL 은 모른다.
  - %s 자리 표시자: 값을 SQL 문자열에 직접 이어 붙이지 않고 따로 넘긴다
    → 사용자가 입력한 글에 따옴표가 있어도 안전하다 (SQL 인젝션 방지)

  함수               SQL                          CRUD
  init_db()          CREATE TABLE IF NOT EXISTS
  list_posts()       SELECT ... ORDER BY          Read (목록)
  get_post(id)       SELECT ... WHERE id = %s     Read (하나)
  create_post(...)   INSERT ... RETURNING         Create
  update_post(...)   UPDATE ... RETURNING         Update
  delete_post(id)    DELETE ...                   Delete
"""
import os

import psycopg
from psycopg.rows import dict_row

# 접속 주소: 환경 변수 DATABASE_URL 이 있으면 그것을, 없으면 docker-compose.yml 의 값을 쓴다
#   postgresql://사용자:비밀번호@호스트:포트/DB이름
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/board")


def connect():
    """DB 연결을 하나 연다.

    row_factory=dict_row : 결과 한 줄을 튜플 (1, '제목') 이 아니라
                           딕셔너리 {"id": 1, "title": "제목"} 으로 받는다 → 그대로 JSON 이 된다.
    with connect() as conn: 으로 쓰면 블록이 끝날 때 자동으로 commit(저장) 하고 연결을 닫는다.
    (블록 안에서 오류가 나면 commit 대신 rollback(취소) 한다)
    """
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    """posts 테이블이 없으면 만든다. 서버가 켜질 때 한 번 실행된다."""
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id          SERIAL PRIMARY KEY,                    -- 1, 2, 3 ... 자동 번호
                title       VARCHAR(100) NOT NULL,                 -- 제목
                writer      VARCHAR(30)  NOT NULL,                 -- 작성자
                content     TEXT         NOT NULL DEFAULT '',      -- 내용
                created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),   -- 쓴 시각
                updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()    -- 고친 시각
            )
            """
        )


# 여러 함수가 같은 열 목록을 쓰므로 한 곳에 모아 둔다
COLUMNS = "id, title, writer, content, created_at, updated_at"


def list_posts():
    """글 목록 - 최근 글이 위로 오게 id 큰 순서. 결과는 딕셔너리의 리스트."""
    with connect() as conn:
        return conn.execute(f"SELECT {COLUMNS} FROM posts ORDER BY id DESC").fetchall()


def get_post(post_id):
    """글 하나. 없으면 None."""
    with connect() as conn:
        return conn.execute(f"SELECT {COLUMNS} FROM posts WHERE id = %s", (post_id,)).fetchone()
        # (post_id,) ← 값이 하나여도 튜플로 넘긴다. 쉼표를 빼먹지 말 것!


def create_post(title, writer, content):
    """새 글 저장. RETURNING 으로 방금 저장된 줄(번호·시각 포함)을 바로 돌려받는다."""
    with connect() as conn:
        return conn.execute(
            f"INSERT INTO posts (title, writer, content) VALUES (%s, %s, %s) RETURNING {COLUMNS}",
            (title, writer, content),
        ).fetchone()


def update_post(post_id, title, writer, content):
    """글 수정. 그 번호의 글이 없으면 None (UPDATE 된 줄이 없으므로)."""
    with connect() as conn:
        return conn.execute(
            f"""
            UPDATE posts
               SET title = %s, writer = %s, content = %s, updated_at = now()
             WHERE id = %s
            RETURNING {COLUMNS}
            """,
            (title, writer, content, post_id),
        ).fetchone()


def delete_post(post_id):
    """글 삭제. 지운 줄 수(rowcount)가 1 이면 True, 없는 글이면 False."""
    with connect() as conn:
        cur = conn.execute("DELETE FROM posts WHERE id = %s", (post_id,))
        return cur.rowcount == 1
