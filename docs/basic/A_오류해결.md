# 부록 A. 자주 만나는 오류와 해결

오류가 나면 먼저 **어디서** 났는지 본다. ① VS Code 터미널(npm, uvicorn, docker), ② 브라우저 화면의 빨간 오류 상자(Vite), ③ 브라우저 F12 → Console 탭, ④ F12 → Network 탭(요청 상태 코드). 오류 문장 안의 **파일 이름과 줄 번호**가 가장 큰 힌트다.

## A-1. 설치·실행

| 증상 | 원인 | 해결 |
|---|---|---|
| `'npm' 용어가 ... 인식되지 않습니다` | Node.js 미설치, 또는 설치 전에 연 터미널 | Node.js 설치 후 VS Code 를 완전히 껐다 켠다 |
| `npm run dev` → `Missing script: "dev"` | `package.json` 이 없는 폴더에서 실행 | `cd` 로 프로젝트 폴더(예: `my-react`)에 들어간다 |
| `'vite' 은(는) 내부 또는 외부 명령...이 아닙니다` | `npm install` 을 안 함 | 그 폴더에서 `npm install` |
| `Port 5173 is in use, trying another one...` | 다른 개발 서버가 5173 을 쓰는 중 | 오류는 아니다. 터미널에 나온 새 주소로 연다. 9장에서는 하나만 켜자 (CORS 는 5173 만 허락) |
| 저장했는데 화면이 안 바뀜 | 파일을 저장 안 함 / 다른 프로젝트의 파일을 고침 | 탭 옆 ● 확인, VS Code 왼쪽 탐색기에서 경로 확인 |

## A-2. JSX·React

| 증상 (오류 문장) | 원인 | 해결 |
|---|---|---|
| `Adjacent JSX elements must be wrapped in an enclosing tag` | return 안에 부모 태그가 둘 이상 | `<div>` 나 `<> </>` 로 감싼다 |
| `Expected corresponding JSX closing tag for 'input'` | `<input>`, `<br>`, `<img>` 를 안 닫음 | `<input />` 처럼 스스로 닫는다 |
| 화면이 하얗고 콘솔에 `... is not defined` | import 를 안 했거나 이름 오타 | 파일 위쪽 `import` 확인. 대소문자까지 같아야 한다 |
| `does not provide an export named 'default'` | 그 파일에 `export default` 가 없음 | 파일 끝에 `export default 컴포넌트이름;` |
| `Too many re-renders` | `onClick={setCount(1)}` 처럼 그릴 때 바로 실행 | `onClick={() => setCount(1)}` |
| `Each child in a list should have a unique "key" prop` | map 으로 만든 태그에 key 가 없음 | 가장 바깥 태그에 `key={item.id}` |
| `Objects are not valid as a React child` | `{user}` 처럼 객체를 그대로 JSX 에 넣음 | `{user.name}` 처럼 글자·숫자를 넣는다 |
| 입력 칸에 글자가 안 쳐짐 | `value` 만 있고 `onChange` 가 없음 | `onChange={e => setX(e.target.value)}` 추가 |
| state 를 바꿨는데 화면이 그대로 | `push`, `obj.x = ...` 로 원본을 직접 고침 | `[...arr, x]`, `{...obj, x}` 로 새로 만든다 |
| `Cannot read properties of null (reading 'title')` | 데이터가 오기 전에 `post.title` 을 그림 | `if (!post) return <p>불러오는 중...</p>;` 를 먼저 |
| `Cannot read properties of undefined (reading 'map')` | 배열 state 의 처음값이 없음 | `useState([])` 처럼 빈 배열로 시작 |
| 콘솔 로그가 두 번씩 찍힘 | 개발 모드의 StrictMode | 정상이다 (8-2 참고) |

## A-3. 서버 통신 (9장)

| 증상 | 원인 | 해결 |
|---|---|---|
| 화면에 "API 서버에 연결할 수 없습니다", 콘솔 `Failed to fetch` | uvicorn 이 꺼져 있음 / 주소 오타 | 터미널 2 에서 `uvicorn main:app --reload`, `config.js` 의 주소 확인 |
| 콘솔 `blocked by CORS policy` | 서버의 CORS 허락 목록에 지금 주소(포트)가 없음 | `main.py` 의 `allow_origins` 확인. React 를 5173 으로 실행 |
| 저장 시 422 | 필수 칸이 비었거나, `Content-Type` 헤더를 빠뜨림 | Network 탭 → Response 의 `detail` 을 읽는다 |
| 404 | 주소 오타(`/api/post`), 없는 글 번호 | Network 탭에서 실제 요청 주소 확인 |
| uvicorn 실행 시 `Could not import module "main"` | `backend` 폴더가 아닌 곳에서 실행 | `cd C:\study\board\backend` 후 실행 |
| uvicorn 실행 시 `connection ... failed` / `Connection refused` (5433) | DB 컨테이너가 꺼져 있음 | `docker compose up -d` 후 `docker compose ps` 가 healthy 인지 |
| `uvicorn` 을 찾을 수 없음 | 가상환경이 안 켜짐 | `.venv\Scripts\Activate.ps1` 후 `(.venv)` 확인 |
| `Activate.ps1 파일을 로드할 수 없습니다` | PowerShell 실행 정책 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 한 번 실행 |
| `pip install -r requirements.txt` → `decoding with 'cp949' codec failed` | requirements.txt 에 한글이 들어 있음 | requirements.txt 에서 한글 주석을 지운다 |

## A-4. Docker

| 증상 | 원인 | 해결 |
|---|---|---|
| `failed to connect to the docker API` / `error during connect` | Docker Desktop 이 꺼져 있음 | Docker Desktop 실행 → Engine running 확인 |
| `Bind for 0.0.0.0:5433 failed: port is already allocated` | 다른 프로그램(컨테이너)이 5433 사용 | `docker ps` 로 확인 후 그 컨테이너를 멈추거나, compose 의 포트를 `"5435:5432"` 로 바꾸고 `db.py` 의 주소도 같이 바꾼다 |
| 한쪽 과정 DB 를 켰더니 다른 과정 DB 컨테이너가 사라짐 | compose 파일에 `name:` 이 없어서 폴더 이름(board)이 겹침 | 저장소의 compose 파일처럼 `name:` 을 붙인다 |
| 글이 모두 사라짐 | `docker compose down -v` 로 볼륨까지 지움 | 되돌릴 수 없다. 평소에는 `stop` 또는 `down`(볼륨 유지)을 쓴다 |
