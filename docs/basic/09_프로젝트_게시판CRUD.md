# 9장. 프로젝트 - FastAPI + PostgreSQL 게시판 CRUD

## 학습 목표

- Docker 로 PostgreSQL 데이터베이스를 띄운다.
- FastAPI 로 게시글 CRUD REST API 를 만들고 `/docs` 에서 시험한다.
- React 에서 `fetch` 로 GET·POST·PUT·DELETE 요청을 보내 게시판을 완성한다.
- CORS 가 무엇이고 왜 서버에서 허락해 줘야 하는지 안다.

## 9-1. 만들 것 한눈에 보기

글 목록 보기, 글 읽기, 글쓰기, 수정, 삭제가 되는 게시판이다. 글은 브라우저가 아니라 **PostgreSQL 데이터베이스**에 저장되므로 새로 고침해도, 브라우저를 껐다 켜도 남는다.

![게시판의 세 부분](../images/fig_architecture.png)

| 부분 | 기술 | 주소 | 실행 방법 |
|---|---|---|---|
| 화면 | React (Vite) | http://localhost:5173 | `npm run dev` |
| API 서버 | FastAPI (uvicorn) | http://localhost:8000 | `uvicorn main:app --reload` |
| 데이터베이스 | PostgreSQL 18 (Docker) | localhost:5433 | `docker compose up -d` |

**API 설계** - 주소와 방식(HTTP 메서드)으로 "무엇을 할지" 를 나타낸다. 이런 규칙을 **REST API** 라고 부른다.

| 하는 일 | 방식 | 주소 | 보내는 것 | 받는 것 (성공 코드) |
|---|---|---|---|---|
| 글 목록 (Read) | GET | `/api/posts` | - | 글 배열 (200) |
| 글 하나 (Read) | GET | `/api/posts/3` | - | 글 객체 (200), 없으면 404 |
| 글쓰기 (Create) | POST | `/api/posts` | `{title, writer, content}` | 저장된 글 (201) |
| 수정 (Update) | PUT | `/api/posts/3` | `{title, writer, content}` | 고친 글 (200) |
| 삭제 (Delete) | DELETE | `/api/posts/3` | - | 내용 없음 (204) |

**작업 순서** - 아래쪽(데이터베이스)부터 위쪽(화면)으로 쌓는다. 아래가 잘 되는지 확인하고 올라가야 문제가 생겨도 어디서 났는지 금방 찾는다.

1. 9-2 Docker 로 PostgreSQL 켜기
2. 9-3 ~ 9-6 FastAPI 서버 만들고 `/docs` 에서 시험
3. 9-7 ~ 9-12 React 화면 만들기

## 9-2. 실습 폴더 준비와 PostgreSQL 켜기

이 장에서는 `C:\study\board` 폴더에 프로젝트를 만든다. 데이터베이스 설정과 API 서버(백엔드)는 **저장소의 완성본을 복사해서 읽으며 이해**하고, React 화면(프론트엔드)은 **직접 만든다.**

**[PS]**

```powershell
mkdir C:\study\board
cd C:\study\board
Copy-Item C:\study\react-fastapi-postgresql\basic\board\docker-compose.yml .
Copy-Item -Recurse C:\study\react-fastapi-postgresql\basic\board\backend .\backend
```

> `Copy-Item 원본 .` 의 마지막 점(`.`)은 "지금 폴더로" 라는 뜻이다.

먼저 **Docker Desktop 을 실행**한다. (시작 메뉴 → Docker Desktop. 왼쪽 아래가 초록색 **Engine running** 이 될 때까지 기다린다.)

<!-- file: basic/board/docker-compose.yml -->

```yaml
# =====================================================================
# 기초 과정 9장 - 게시판 데이터베이스 (PostgreSQL 18) 를 Docker 로 실행
#
#   시작        : docker compose up -d        (이 파일이 있는 폴더에서)
#   상태 확인   : docker compose ps           (STATUS 가 healthy 이면 준비 완료)
#   로그 보기   : docker compose logs -f db   (Ctrl+C 로 빠져나옴)
#   멈추기      : docker compose stop         (데이터는 남는다)
#   완전히 지우기: docker compose down -v      (컨테이너 + 데이터 볼륨 삭제, 되돌릴 수 없음)
#
# 접속 정보 (FastAPI·DBeaver 공통)
#   호스트 localhost / 포트 5433 / DB board / 사용자 postgres / 비밀번호 postgres
#   ※ 5432 가 아니라 5433 이다. 다른 과정에서 만든 PostgreSQL(5432)과 겹치지 않게 하려고.
# =====================================================================

# 프로젝트 이름. 적지 않으면 "폴더 이름"(board)이 프로젝트 이름이 되는데,
# 기초·심화 두 과정의 폴더 이름이 모두 board 라서 서로를 같은 프로젝트로 보고
# 한쪽을 켜면 다른 쪽 컨테이너를 지워 버린다. 이름을 따로 붙여 이 문제를 막는다.
name: react-basic-board

services:
  db:
    image: postgres:18                # Docker Hub 의 공식 PostgreSQL 18 이미지
    container_name: react-board-db    # docker 명령에서 부를 컨테이너 이름
    restart: unless-stopped           # Docker Desktop 이 켜지면 자동으로 다시 시작
    ports:
      - "5433:5432"                   # "내 PC 포트:컨테이너 포트"
    environment:
      POSTGRES_USER: postgres         # 관리자 계정
      POSTGRES_PASSWORD: postgres     # 실습용 비밀번호 (실제 서비스에서는 절대 이렇게 쓰지 않는다)
      POSTGRES_DB: board              # 처음 시작할 때 만들어 둘 데이터베이스 이름
      TZ: Asia/Seoul
    command: ["postgres", "-c", "timezone=Asia/Seoul"]   # now() 가 한국 시간으로 나오게
    volumes:
      - board_data:/var/lib/postgresql   # 데이터는 볼륨에 → 컨테이너를 지워도 글이 남는다
    healthcheck:                         # "접속 받을 준비가 됐나?" 를 5초마다 검사
      test: ["CMD-SHELL", "pg_isready -U postgres -d board"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  board_data:                         # Docker 가 관리하는 저장 공간
```

**[PS]** `C:\study\board` 에서

```powershell
docker compose up -d
```

처음에는 `postgres:18` 이미지를 받느라 `Pulling` 줄이 여러 개 나오며 1~2분 걸린다. 끝나면 이렇게 나온다.

```text
 Network react-basic-board_default Created
 Volume react-basic-board_board_data Created
 Container react-board-db Created
 Container react-board-db Started
```

**[PS]** 상태 확인

```powershell
docker compose ps
```

```text
NAME             IMAGE         COMMAND                   SERVICE   CREATED         STATUS                   PORTS
react-board-db   postgres:18   "docker-entrypoint.s…"   db        8 seconds ago   Up 7 seconds (healthy)   0.0.0.0:5433->5432/tcp, [::]:5433->5432/tcp
```

`STATUS` 에 **(healthy)** 가 보이면 접속할 준비가 된 것이다. `(health: starting)` 이면 몇 초 뒤 다시 확인한다.

> **name: 줄이 꼭 필요한 이유** compose 는 `name:` 이 없으면 **폴더 이름**을 프로젝트 이름으로 쓴다. 심화 과정 폴더도 이름이 `board` 라서, 이름을 안 붙이면 한쪽을 켤 때 다른 쪽 컨테이너를 지워 버린다. 실제로 이 교안을 만들다가 겪은 일이다.

## 9-3. FastAPI 서버 준비 (가상환경)

파이썬 패키지는 프로젝트마다 따로 설치하는 것이 좋다. 그 "프로젝트 전용 설치 공간" 이 **가상환경**(`.venv`)이다.

**[PS]** 새 터미널(+)을 열고

```powershell
cd C:\study\board\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

가상환경이 켜지면 프롬프트 앞에 `(.venv)` 가 붙는다. 설치가 끝나면 마지막에 `Successfully installed ... fastapi-0.162.2 ... psycopg-3.3.8 ...` 같은 줄이 나온다.

> **`이 시스템에서 스크립트를 실행할 수 없으므로 ...Activate.ps1 파일을 로드할 수 없습니다`** 오류가 나면 PowerShell 의 스크립트 실행이 막혀 있는 것이다. 아래 명령을 **한 번만** 실행하고 다시 `.venv\Scripts\Activate.ps1` 을 친다.
>
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

<!-- file: basic/board/backend/requirements.txt -->

```text
# Basic course board API (install: pip install -r requirements.txt)
# NOTE: keep this file ASCII-only. pip on Korean Windows may fail to read non-ASCII text.
fastapi==0.162.2            # web API framework
uvicorn[standard]==0.54.0   # server that runs FastAPI
psycopg[binary]==3.3.8      # PostgreSQL driver
```

> requirements.txt 의 주석을 영어로 쓴 이유: 한국어 Windows 에서 pip 가 이 파일을 cp949 로 읽다가 한글 주석 때문에 `decoding with 'cp949' codec failed` 오류를 내는 경우가 있다. **requirements.txt 에는 한글을 쓰지 말자.**

## 9-4. db.py - SQL 을 실행하는 함수들

서버 코드는 두 파일로 나눈다. `db.py` 는 **데이터베이스 담당**, `main.py` 는 **API(주소) 담당**이다.

<!-- file: basic/board/backend/db.py -->

```python
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
```

- `%s` 자리에 값을 따로 넘기는 것이 중요하다. 사용자가 제목에 `'` 같은 글자를 넣어도 SQL 이 깨지지 않는다(SQL 인젝션 방지).
- `RETURNING` 은 INSERT·UPDATE 하자마자 그 줄을 돌려받는 PostgreSQL 문법이다. 새 글의 번호(id)와 저장 시각을 바로 화면에 쓸 수 있다.

## 9-5. main.py - API 주소 만들기

<!-- file: basic/board/backend/main.py -->

```python
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
```

**CORS 가 뭐길래?** 브라우저는 보안을 위해, 지금 페이지의 **출처**(origin = 프로토콜 + 호스트 + 포트)와 다른 출처로 보내는 요청의 응답을 기본으로 막는다. React 는 `http://localhost:5173`, API 는 `http://localhost:8000` 이므로 포트가 달라 **다른 출처**다. 서버가 응답 헤더로 "5173 에서 온 요청은 괜찮아" 라고 말해 줘야 브라우저가 응답을 React 에게 넘긴다. 그 설정이 `CORSMiddleware` 다.

CORS 설정을 빼면 브라우저 콘솔(F12)에 이런 빨간 오류가 뜬다.

```text
Access to fetch at 'http://localhost:8000/api/posts' from origin 'http://localhost:5173'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

> CORS 는 **브라우저**가 하는 검사다. `/docs` 나 파이썬·curl 로 보내는 요청에는 적용되지 않는다. "/docs 에서는 되는데 React 에서는 안 된다" 면 CORS 를 의심하자.

| 상태 코드 | 뜻 | 이 서버에서 |
|---|---|---|
| 200 OK | 성공 | 목록, 읽기, 수정 |
| 201 Created | 새로 만들었음 | 글쓰기 |
| 204 No Content | 성공, 돌려줄 내용 없음 | 삭제 |
| 400 Bad Request | 잘못된 요청 | 빈칸만 있는 제목 |
| 404 Not Found | 없음 | 없는 글 번호 |
| 422 Unprocessable Entity | 입력 모양이 규칙에 안 맞음 | 제목이 빈 글자, 100자 초과 (FastAPI 가 자동 검사) |

## 9-6. 서버 실행과 /docs 에서 시험하기

**[PS]** `(.venv)` 가 붙은 터미널, `C:\study\board\backend` 에서

```powershell
uvicorn main:app --reload
```

```text
INFO:     Will watch for changes in these directories: ['C:\\study\\board\\backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [...] using WatchFiles
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

`main:app` 은 "main.py 파일 안의 app 변수" 라는 뜻이고, `--reload` 는 코드를 고쳐 저장하면 서버를 자동으로 다시 켜 준다. 서버가 켜질 때 `lifespan` 의 `db.init_db()` 가 실행되어 posts 테이블이 만들어진다.

브라우저에서 **http://localhost:8000/docs** 를 연다. FastAPI 가 만들어 주는 API 시험 화면이다.

![FastAPI 가 자동으로 만든 /docs 화면](../images/b9_docs.png)

1. **POST /api/posts** 를 눌러 펼치고 **Try it out** 을 누른다.
2. Request body 를 아래처럼 고치고 **Execute**.

```json
{
  "title": "React 게시판 첫 글입니다",
  "writer": "민수",
  "content": "FastAPI 와 PostgreSQL 에 저장된 글입니다."
}
```

3. 아래 Responses 에 **Code 201** 과 함께 저장된 글이 나온다.

```json
{
  "id": 1,
  "title": "React 게시판 첫 글입니다",
  "writer": "민수",
  "content": "FastAPI 와 PostgreSQL 에 저장된 글입니다.",
  "created_at": "2026-11-20T09:37:30.266017+09:00",
  "updated_at": "2026-11-20T09:37:30.266017+09:00"
}
```

4. 글을 두세 개 더 쓰고, **GET /api/posts** 를 Execute 해서 목록이 오는지 본다. 브라우저 주소창에 `http://localhost:8000/api/posts` 를 직접 쳐도 JSON 이 보인다.
5. 제목을 빈 글자(`""`)로 보내 보자. **422** 와 함께 `"String should have at least 1 character"` 이 온다. FastAPI(Pydantic)가 `Field(min_length=1)` 규칙으로 막은 것이다.

**데이터베이스에 정말 들어갔을까?** 컨테이너 안의 psql 로 직접 확인해 보자.

**[PS]**

```powershell
docker exec react-board-db psql -U postgres -d board -c "SELECT id, title, writer, created_at FROM posts ORDER BY id;"
```

```text
 id |           title            | writer |          created_at
----+----------------------------+--------+-------------------------------
  1 | React 게시판 첫 글입니다   | 민수   | 2026-11-20 09:37:30.266017+09
  2 | useEffect 로 목록 불러오기 | 지수   | 2026-11-20 09:37:32.352978+09
  3 | CORS 오류가 났을 때        | 현우   | 2026-11-20 09:37:34.452626+09
  4 | 오늘 배운 useState 정리    | 서연   | 2026-11-20 09:37:36.529576+09
(4 rows)
```

내 화면에는 내가 쓴 글이 나온다. 여기까지 되면 백엔드는 완성이다. **서버 터미널은 켜 둔 채로** 다음으로 넘어간다.

## 9-7. React 프로젝트 만들기

**[PS]** 새 터미널(+)을 열고

```powershell
cd C:\study\board
npm create vite@latest frontend -- --template react --no-interactive
cd frontend
npm install
```

1장에서처럼 정리한다.

1. `src/App.css`, `src/index.css` 의 내용을 지운다. (`App.css` 는 9-12 에서 채운다)
2. `src/assets` 폴더는 쓰지 않으니 지워도 된다.
3. `src/components` 폴더를 만든다.

완성하면 폴더는 이렇게 된다.

```text
C:\study\board
├─ docker-compose.yml
├─ backend
│  ├─ .venv
│  ├─ db.py
│  ├─ main.py
│  └─ requirements.txt
└─ frontend
   ├─ index.html
   └─ src
      ├─ main.jsx
      ├─ App.jsx               ← 화면 전환 (어떤 화면을 보여 줄지)
      ├─ App.css               ← 게시판 모양
      ├─ config.js             ← API 주소, 날짜 바꾸기 함수
      └─ components
         ├─ PostList.jsx       ← 목록      (GET 목록)
         ├─ PostDetail.jsx     ← 글 읽기   (GET 하나, DELETE)
         └─ PostForm.jsx       ← 글쓰기·수정 (POST, PUT)
```

## 9-8. config.js 와 App.jsx - 화면 전환

API 주소는 여러 파일에서 쓰므로 한 곳에 둔다.

<!-- file: basic/board/frontend/src/config.js -->

```js
// config.js - 여러 파일이 함께 쓰는 설정 값
//
// API 서버(FastAPI) 주소. 서버 주소가 바뀌면 이 한 줄만 고치면 된다.
export const API_URL = "http://localhost:8000/api";

// 날짜 글자 "2026-11-20T10:30:00.123+09:00" → "2026. 11. 20. 오전 10:30" 처럼 읽기 좋게 바꾼다
export function formatDate(text) {
  return new Date(text).toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
```

이 게시판은 화면이 세 가지(목록·읽기·글쓰기/수정)다. **"지금 어떤 화면인가"** 를 App 의 state 하나로 관리하고, 화면을 바꾸는 함수를 자식들에게 props 로 내려준다 (6-5 state 끌어올리기).

![기초 게시판의 화면 전환](../images/fig_board_pages.png)

<!-- file: basic/board/frontend/src/App.jsx -->

```jsx
// App.jsx - 게시판의 "화면 전환" 을 맡는 부모 컴포넌트
//
// 이 파일이 보여 주는 것
//   - 지금 어떤 화면을 보여 줄지를 state 하나(page)로 관리한다.
//       { name: "list" }              → 글 목록
//       { name: "detail", id: 3 }     → 3번 글 읽기
//       { name: "form" }              → 글쓰기
//       { name: "form",   id: 3 }     → 3번 글 수정
//   - 화면을 바꾸는 함수(go...)를 자식에게 props 로 내려준다 (6장 state 끌어올리기).
//   - 조건부 렌더링(5장)으로 page.name 에 맞는 컴포넌트 하나만 그린다.
//
//   ※ 이 방식은 주소창의 주소가 바뀌지 않는다. 그래서 새로 고침하면 목록으로 돌아가고,
//     "3번 글" 주소를 친구에게 보낼 수도 없다. 심화 과정에서 React Router 로 해결한다.

import { useState } from "react";
import PostList from "./components/PostList";
import PostDetail from "./components/PostDetail";
import PostForm from "./components/PostForm";
import "./App.css";

function App() {
  const [page, setPage] = useState({ name: "list" }); // 처음 화면은 목록

  // 화면을 바꾸는 함수들 - 자식 컴포넌트가 불러서 쓴다
  const goList = () => setPage({ name: "list" });
  const goDetail = (id) => setPage({ name: "detail", id });
  const goForm = (id) => setPage({ name: "form", id }); // id 가 없으면 글쓰기, 있으면 수정

  return (
    <div className="container">
      <header className="header">
        {/* 제목을 누르면 언제든 목록으로 */}
        <h1 onClick={goList}>📋 React 게시판</h1>
        <span className="badge">FastAPI + PostgreSQL</span>
      </header>

      {page.name === "list" && <PostList onSelect={goDetail} onWrite={() => goForm()} />}
      {page.name === "detail" && (
        <PostDetail id={page.id} onBack={goList} onEdit={goForm} onDeleted={goList} />
      )}
      {page.name === "form" && (
        <PostForm
          id={page.id}
          onSaved={goDetail} // 저장이 끝나면 그 글 읽기 화면으로
          onCancel={() => (page.id ? goDetail(page.id) : goList())} // 수정 취소 → 글로, 글쓰기 취소 → 목록으로
        />
      )}
    </div>
  );
}

export default App;
```

> 이 단계에서는 아직 세 컴포넌트 파일이 없어서 오류 화면이 뜬다. 9-9 ~ 9-11 에서 하나씩 만들면 사라진다.

## 9-9. PostList - 목록 (Read)

8장의 Ex0802Fetch 와 같은 모양이다. 주소만 FastAPI 서버로 바뀌었다.

<!-- file: basic/board/frontend/src/components/PostList.jsx -->

```jsx
// PostList.jsx - 글 목록 화면 (CRUD 의 R: Read 목록)
//
// 이 파일이 보여 주는 것
//   - 화면에 처음 나타날 때 useEffect(..., []) 로 GET /api/posts 를 한 번 요청한다 (8장).
//   - loading / error / posts 세 state 로 "불러오는 중 · 실패 · 목록" 을 나눠 그린다.
//   - 제목을 누르면 부모(App)가 내려준 onSelect(id) 를 불러 읽기 화면으로 바꾼다.

import { useEffect, useState } from "react";
import { API_URL, formatDate } from "../config";

function PostList({ onSelect, onWrite }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_URL}/posts`); // GET 은 fetch(주소) 만 쓰면 된다
        if (!res.ok) throw new Error(`목록을 불러오지 못했습니다 (${res.status})`);
        setPosts(await res.json()); // JSON 배열 → 자바스크립트 배열
      } catch (err) {
        // 서버가 꺼져 있으면 fetch 자체가 실패한다 (TypeError: Failed to fetch)
        setError(err.message === "Failed to fetch" ? "API 서버에 연결할 수 없습니다. 서버가 켜져 있나요?" : err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []); // [] → 처음 한 번만

  if (loading) return <p className="info">⏳ 불러오는 중...</p>;
  if (error) return <p className="error">⚠️ {error}</p>;

  return (
    <div>
      <div className="toolbar">
        <span>전체 {posts.length}개</span>
        <button className="primary" onClick={onWrite}>
          ✏️ 글쓰기
        </button>
      </div>

      {posts.length === 0 ? (
        <p className="info">아직 글이 없습니다. 첫 글을 써 보세요!</p>
      ) : (
        <table className="post-table">
          <thead>
            <tr>
              <th className="col-id">번호</th>
              <th>제목</th>
              <th className="col-writer">작성자</th>
              <th className="col-date">작성일</th>
            </tr>
          </thead>
          <tbody>
            {posts.map((post) => (
              <tr key={post.id}>
                <td className="col-id">{post.id}</td>
                <td>
                  {/* 링크처럼 보이지만 주소 이동이 아니라 state 를 바꾸는 버튼 */}
                  <button className="link" onClick={() => onSelect(post.id)}>
                    {post.title}
                  </button>
                </td>
                <td className="col-writer">{post.writer}</td>
                <td className="col-date">{formatDate(post.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default PostList;
```

## 9-10. PostDetail - 글 읽기 (Read) 와 삭제 (Delete)

<!-- file: basic/board/frontend/src/components/PostDetail.jsx -->

```jsx
// PostDetail.jsx - 글 읽기 화면 (R: Read 하나 + D: Delete)
//
// 이 파일이 보여 주는 것
//   - props 로 받은 id 의 글을 GET /api/posts/{id} 로 불러온다.
//     useEffect 의 의존성 배열에 [id] 를 넣어, id 가 바뀌면 다시 불러온다.
//   - 삭제: confirm 으로 한 번 더 묻고 → DELETE /api/posts/{id} → 성공(204)하면 목록으로.
//   - 404(없는 글)도 오류 문구로 보여 준다.

import { useEffect, useState } from "react";
import { API_URL, formatDate } from "../config";

function PostDetail({ id, onBack, onEdit, onDeleted }) {
  const [post, setPost] = useState(null); // 아직 못 받았으면 null
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_URL}/posts/${id}`);
        if (res.status === 404) throw new Error("글을 찾을 수 없습니다. 이미 지워졌을 수 있어요.");
        if (!res.ok) throw new Error(`글을 불러오지 못했습니다 (${res.status})`);
        setPost(await res.json());
      } catch (err) {
        setError(err.message);
      }
    }
    load();
  }, [id]);

  const handleDelete = async () => {
    if (!confirm("정말 삭제할까요? 되돌릴 수 없습니다.")) return; // 취소를 누르면 여기서 끝
    // fetch 의 두 번째 인자로 "방식(method)" 을 정한다. 기본값은 GET
    const res = await fetch(`${API_URL}/posts/${id}`, { method: "DELETE" });
    if (res.ok) {
      onDeleted(); // 부모에게 "지웠어요" → 목록 화면으로
    } else {
      alert(`삭제하지 못했습니다 (${res.status})`);
    }
  };

  if (error)
    return (
      <div>
        <p className="error">⚠️ {error}</p>
        <button onClick={onBack}>목록</button>
      </div>
    );
  if (!post) return <p className="info">⏳ 불러오는 중...</p>;

  return (
    <article className="post-detail">
      <h2>{post.title}</h2>
      <div className="meta">
        {post.writer} · {formatDate(post.created_at)}
        {/* 고친 적이 있으면 고친 시각도 보여 준다 */}
        {post.updated_at !== post.created_at && ` · 수정 ${formatDate(post.updated_at)}`}
      </div>
      {/* 줄바꿈을 그대로 보이게 하려고 CSS 에 white-space: pre-wrap 을 주었다 */}
      <div className="content">{post.content || "(내용 없음)"}</div>

      <div className="buttons">
        <button onClick={onBack}>목록</button>
        <button onClick={() => onEdit(post.id)}>수정</button>
        <button className="danger" onClick={handleDelete}>
          삭제
        </button>
      </div>
    </article>
  );
}

export default PostDetail;
```

`fetch` 의 두 번째 인자로 요청 방식을 정한다. GET 은 기본값이라 생략했고, 삭제는 `{ method: "DELETE" }` 를 넘긴다.

## 9-11. PostForm - 글쓰기 (Create) 와 수정 (Update)

<!-- file: basic/board/frontend/src/components/PostForm.jsx -->

```jsx
// PostForm.jsx - 글쓰기 / 수정 화면 (C: Create, U: Update)
//
// 이 파일이 보여 주는 것
//   - 하나의 폼으로 글쓰기와 수정을 함께 처리한다.
//       id 가 없으면 → 빈 폼 → POST /api/posts         (새 글)
//       id 가 있으면 → 그 글을 불러와 폼을 채움 → PUT /api/posts/{id}  (수정)
//   - 입력 칸 여러 개를 객체 state 하나(form)로 관리한다 (7장 Ex0702Form 과 같은 모양).
//   - JSON 을 보낼 때는 method, headers(Content-Type), body(JSON.stringify) 세 가지를 쓴다.
//   - 저장 중에는 버튼을 막아(disabled) 두 번 눌러 글이 두 개 생기는 일을 막는다.

import { useEffect, useState } from "react";
import { API_URL } from "../config";

const EMPTY = { title: "", writer: "", content: "" };

function PostForm({ id, onSaved, onCancel }) {
  const isEdit = id !== undefined; // 수정 화면인가?
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // 수정 화면이면 원래 글을 불러와 폼에 채운다
  useEffect(() => {
    if (!isEdit) return; // 글쓰기면 할 일 없음
    async function load() {
      const res = await fetch(`${API_URL}/posts/${id}`);
      if (!res.ok) {
        setError("글을 불러오지 못했습니다");
        return;
      }
      const post = await res.json();
      // 서버가 준 글에는 id, created_at 등도 있지만 폼에는 세 칸만 필요하다
      setForm({ title: post.title, writer: post.writer, content: post.content });
    }
    load();
  }, [id, isEdit]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.writer.trim()) {
      setError("제목과 작성자를 입력하세요.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(isEdit ? `${API_URL}/posts/${id}` : `${API_URL}/posts`, {
        method: isEdit ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" }, // "본문은 JSON 입니다" 라고 알린다
        body: JSON.stringify(form), //                      객체 → JSON 글자
      });
      if (!res.ok) throw new Error(`저장하지 못했습니다 (${res.status})`);
      const saved = await res.json(); // 서버가 돌려준 글 (새 글이면 새 번호가 들어 있다)
      onSaved(saved.id); //              부모에게 알림 → 그 글 읽기 화면으로
    } catch (err) {
      setError(err.message);
      setSaving(false); // 실패했을 때만 버튼을 다시 살린다 (성공하면 화면이 바뀐다)
    }
  };

  return (
    <form className="post-form" onSubmit={handleSubmit}>
      <h2>{isEdit ? `${id}번 글 수정` : "새 글 쓰기"}</h2>
      {error && <p className="error">⚠️ {error}</p>}

      <label>
        제목
        <input name="title" value={form.title} onChange={handleChange} maxLength={100} />
      </label>
      <label>
        작성자
        <input name="writer" value={form.writer} onChange={handleChange} maxLength={30} />
      </label>
      <label>
        내용
        <textarea name="content" value={form.content} onChange={handleChange} rows={8} />
      </label>

      <div className="buttons">
        <button type="button" onClick={onCancel}>
          취소
        </button>
        {/* type="button" 이 아닌 버튼은 submit → onSubmit 실행 */}
        <button type="submit" className="primary" disabled={saving}>
          {saving ? "저장 중..." : "저장"}
        </button>
      </div>
    </form>
  );
}

export default PostForm;
```

JSON 을 보내는 fetch 는 세 가지를 꼭 넣는다.

```jsx
fetch(주소, {
  method: "POST",                                   // ① 방식
  headers: { "Content-Type": "application/json" },  // ② "본문은 JSON 입니다"
  body: JSON.stringify(form),                       // ③ 객체 → JSON 글자
});
```

`Content-Type` 을 빠뜨리면 브라우저가 글자 본문을 `text/plain` 으로 보내고, FastAPI 는 본문을 JSON 객체로 읽지 못해 **422** (`Input should be a valid dictionary ...`)를 돌려준다.

## 9-12. App.css - 모양 입히기

<!-- file: basic/board/frontend/src/App.css -->

```css
/* App.css - 게시판 화면 꾸미기 (CSS 는 HTML 수업 때와 똑같다. className 으로 연결) */

.container {
  max-width: 820px;
  margin: 0 auto;
  padding: 20px;
}

/* ---------- 머리글 */
.header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 12px;
  margin-bottom: 16px;
  border-bottom: 3px solid #61dafb;
}

.header h1 {
  margin: 0;
  font-size: 24px;
  color: #1f3a5f;
  cursor: pointer;
}

.badge {
  padding: 2px 8px;
  border-radius: 10px;
  background: #eef3f8;
  color: #03588c;
  font-size: 12px;
}

/* ---------- 버튼 */
button {
  padding: 6px 14px;
  border: 1px solid #c9d3df;
  border-radius: 6px;
  background: white;
  font-family: inherit; /* 버튼은 기본으로 다른 글꼴을 쓰므로 바깥 글꼴을 물려받게 한다 */
  font-size: 14px;
  cursor: pointer;
}

button:hover {
  background: #f2f6fa;
}

button.primary {
  border-color: #03588c;
  background: #03588c;
  color: white;
}

button.danger {
  border-color: #c0392b;
  color: #c0392b;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 링크처럼 보이는 버튼 (목록의 제목) */
button.link {
  padding: 0;
  font-size: 15px;
  border: none;
  background: none;
  color: #1f3a5f;
  text-align: left;
}

button.link:hover {
  text-decoration: underline;
}

/* ---------- 목록 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  color: #6b7280;
}

.post-table {
  width: 100%;
  border-collapse: collapse;
}

.post-table th {
  padding: 9px 6px;
  background: #1f3a5f;
  color: white;
  font-weight: normal;
}

.post-table td {
  padding: 9px 6px;
  font-size: 15px;
  border-bottom: 1px solid #e5e9ef;
}

.col-id,
.col-writer {
  width: 80px;
  text-align: center;
}

.col-date {
  width: 190px;
  text-align: center;
  color: #6b7280;
  font-size: 13px;
}

/* ---------- 읽기 */
.post-detail h2 {
  margin: 0 0 6px;
}

.meta {
  padding-bottom: 10px;
  border-bottom: 1px solid #e5e9ef;
  color: #6b7280;
  font-size: 13px;
}

.content {
  min-height: 120px;
  padding: 16px 2px;
  white-space: pre-wrap; /* 내용의 줄바꿈을 그대로 보여 준다 */
  line-height: 1.7;
}

.buttons {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  margin-top: 12px;
}

/* ---------- 글쓰기·수정 */
.post-form label {
  display: block;
  margin-bottom: 12px;
  font-weight: bold;
  color: #374151;
}

.post-form input,
.post-form textarea {
  display: block;
  box-sizing: border-box;
  width: 100%;
  margin-top: 4px;
  padding: 8px;
  border: 1px solid #c9d3df;
  border-radius: 6px;
  font: inherit;
  font-weight: normal;
}

/* ---------- 안내·오류 문구 */
.info {
  padding: 20px;
  text-align: center;
  color: #6b7280;
}

.error {
  padding: 10px 12px;
  border-radius: 6px;
  background: #fdecea;
  color: #c0392b;
}
```

`src/index.css` 에는 1-4 의 내용(글꼴·여백)을 넣는다.

## 9-13. 전체 실행하기

세 가지가 모두 켜져 있어야 한다. 터미널 세 개를 쓰는 것이 편하다.

| 터미널 | 폴더 | 명령 | 확인 |
|---|---|---|---|
| 1 | `C:\study\board` | `docker compose up -d` (한 번 켜 두면 됨) | `docker compose ps` 가 healthy |
| 2 | `C:\study\board\backend` | `.venv\Scripts\Activate.ps1` → `uvicorn main:app --reload` | http://localhost:8000/docs |
| 3 | `C:\study\board\frontend` | `npm run dev` | http://localhost:5173 |

http://localhost:5173 을 열면 게시판이 나온다.

![글 목록 (PostList)](../images/b9_list.png)

**글쓰기** 버튼 → 제목·작성자·내용 입력 → **저장**.

![글쓰기 (PostForm)](../images/b9_form.png)

저장하면 방금 쓴 글의 읽기 화면으로 바뀐다. **수정**, **삭제**(확인 창이 뜬다)도 해 보자.

![글 읽기 (PostDetail)](../images/b9_detail.png)

> **서버 쪽 터미널도 함께 보자.** 화면에서 무언가를 할 때마다 uvicorn 터미널에 `"GET /api/posts HTTP/1.1" 200 OK`, `"POST /api/posts HTTP/1.1" 201 Created` 같은 줄이 찍힌다. 글쓰기·수정·삭제 때는 그 앞에 `OPTIONS` 요청이 먼저 보이는데, 브라우저가 "이 요청 보내도 돼?" 하고 CORS 를 미리 물어보는 **사전 요청(preflight)** 이다.

**F12 → Network 탭**을 열어 두고 글쓰기를 해 보면, `posts` 요청을 눌러 **Payload**(보낸 JSON)와 **Response**(받은 JSON)를 직접 볼 수 있다. 무언가 안 될 때 가장 먼저 볼 곳이다.

> 내 코드가 잘 안 되면 저장소의 완성본(`basic/board/frontend`)에서 `npm install` → `npm run dev` 로 실행해 비교해 보자. 완성본과 내 프로젝트를 동시에 켜면 하나는 5174 번 포트로 뜨는데, **CORS 는 5173 만 허락**했으므로 5174 쪽은 목록을 못 불러온다. 하나만 켜자.

## 9-14. 끝내기와 다시 시작하기

| 하고 싶은 일 | 명령 |
|---|---|
| React·FastAPI 끄기 | 각 터미널에서 **Ctrl+C** |
| DB 잠시 멈추기 (데이터 유지) | `docker compose stop` |
| DB 다시 켜기 | `docker compose up -d` |
| DB 와 **모든 글 삭제** | `docker compose down -v` (되돌릴 수 없음) |

다음 날 다시 할 때는 9-13 의 표 순서대로 세 가지를 켜면 된다. 글은 Docker 볼륨에 저장되어 있어서 그대로 남아 있다.

## 9-15. 도전 과제

스스로 해 보는 확장 과제다. 정답은 없고, 심화 과정에서 비슷한 기능을 만든다.

1. **글 개수 표시 꾸미기** - 목록 위에 "오늘 쓴 글 N개" 를 함께 보여 주기. (`created_at` 의 날짜를 오늘 날짜와 비교)
2. **검색** - 목록 위에 검색 칸을 두고, 제목에 검색어가 들어간 글만 보여 주기. (서버는 그대로 두고 React 에서 `filter`)
3. **조회수** - `posts` 에 `views` 열을 추가하고, 글을 읽을 때마다 1 올리기. (백엔드: `ALTER TABLE` 또는 `CREATE TABLE` 고치기 + `UPDATE ... SET views = views + 1`)

> 2번 검색을 서버 쪽에서 하고 싶다면 `GET /api/posts?q=검색어` 처럼 쿼리 매개변수를 받아 `WHERE title ILIKE %s` 로 찾으면 된다.

## 정리

- 아래부터 쌓는다: DB(Docker) → API(FastAPI, /docs 로 확인) → 화면(React).
- REST API: 같은 주소라도 방식(GET·POST·PUT·DELETE)으로 하는 일을 구분한다.
- React 는 `fetch(주소, { method, headers, body })` 로 요청하고, `res.ok` 로 성공을 확인한다.
- 다른 출처(포트)의 API 를 부르려면 서버에서 **CORS** 를 허락해야 한다.
- 기초 게시판은 state 로 화면을 바꾸므로 **주소가 바뀌지 않는다.** 새로 고침하면 목록으로 돌아가고, 3번 글 주소를 친구에게 보낼 수도 없다. → 심화 과정에서 **React Router** 로 해결한다.

## 확인 문제

1. 글 수정 요청의 방식과 주소, 성공했을 때의 상태 코드를 쓰시오.
2. React 화면에서 글 목록이 안 나오고, 콘솔에 `blocked by CORS policy` 오류가 보인다. 무엇을 확인해야 하는가?
3. PostForm 에서 `headers: { "Content-Type": "application/json" }` 을 지우면 저장할 때 어떤 일이 생기는지 직접 해 보고, Network 탭의 상태 코드를 쓰시오.
4. 서버(uvicorn)를 끈 상태에서 목록 화면을 새로 고치면 어떤 문구가 보이는가? 그 문구는 어느 파일의 어느 코드에서 나온 것인가?
5. `docker compose down` 과 `docker compose down -v` 의 차이를 쓰시오.
