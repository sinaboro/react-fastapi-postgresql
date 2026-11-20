# 부록 A. 자주 만나는 오류와 해결

기초 교안 부록 A 의 내용(설치, JSX, CORS, Docker 등)도 그대로 해당된다. 여기서는 심화 과정에서 새로 만나는 것만 모았다.

## A-1. Hook·Context

| 증상 | 원인 | 해결 |
|---|---|---|
| `Cannot read properties of null (reading 'focus')` | 화면이 그려지기 전에 `ref.current` 를 씀, 또는 `ref={...}` 연결을 빠뜨림 | useEffect 나 이벤트 안에서 쓰기, 태그에 `ref` 확인 |
| `모르는 action: ...` (리듀서의 default 오류) | dispatch 의 type 오타 | 리듀서의 case 이름과 똑같이 |
| 리듀서로 바꿨는데 화면이 안 바뀜 | 리듀서에서 `state.push` 등 원본을 고치고 같은 state 를 return | 새 배열·객체를 return |
| `useTheme 은 <ThemeProvider> 안에서만 ...`, `useAuth 는 <AuthProvider> 안에서만 ...` | Provider 로 감싸지 않은 곳에서 사용 | main.jsx(또는 상위)에서 Provider 로 감쌌는지 확인 |
| `Invalid hook call` | 일반 함수·조건문 안에서 Hook 을 부름 | Hook 은 컴포넌트·커스텀 훅의 맨 위에서만 |
| 커스텀 훅에서 무한 요청 | useEffect 의존성에 매번 새로 만들어지는 함수·객체를 넣음 | `useApi(fn, [id])` 처럼 값(deps)만 넣기 |

## A-2. React Router

| 증상 | 원인 | 해결 |
|---|---|---|
| `useNavigate() may be used only in the context of a <Router> component` | `<BrowserRouter>` 로 감싸지 않음, 또는 Router 바깥 컴포넌트에서 사용 | main.jsx 에서 `<BrowserRouter>` 로 App 을 감싼다 (AuthProvider 보다 바깥) |
| `Failed to resolve import "react-router"` | 패키지를 설치하지 않음 | `npm install react-router` |
| 링크를 누르면 화면이 깜빡이고 state 가 사라짐 | `<a href>` 사용 | `<Link to>` 로 바꾼다 |
| 화면이 안 바뀌고 머리글만 보임 | Layout 에 `<Outlet />` 이 없음 | 자식 화면이 들어갈 자리에 `<Outlet />` |
| `useParams()` 값이 `undefined` | Route path 의 이름과 꺼내는 이름이 다름 (`:id` vs `postId`) | 이름을 똑같이 |
| id 비교가 항상 false | 주소 값은 문자열 (`"2" === 2` 는 false) | `Number(id)` 로 바꿔 비교 |
| 메뉴 "홈" 이 항상 active | `/` 는 모든 주소의 앞부분 | `<NavLink to="/" end>` |

## A-3. 로그인·JWT

| 증상 | 원인 | 해결 |
|---|---|---|
| 로그인했는데 글쓰기가 401 | 요청에 Authorization 헤더가 없음 | Network 탭 → Request Headers 확인. api.js 의 `request` 에서 토큰을 붙이는지 |
| 모든 요청이 401 "로그인이 만료되었습니다" | 토큰 만료, 또는 서버의 SECRET_KEY 가 바뀜(서버 재시작 시 환경 변수 변경) | 다시 로그인 |
| 로그인했다가 새로 고침하면 로그아웃됨 | 토큰을 localStorage 에 저장하지 않음, 또는 시작할 때 `/me` 복원 코드 누락 | AuthContext 의 login, 첫 useEffect 확인 |
| `/posts/new` 에서 F5 → 잠깐 로그인 화면으로 튕김 | 토큰 확인이 끝나기 전에 ProtectedRoute 가 user=null 로 판단 | AuthProvider 의 `ready` 처리 |
| 회원가입 422 "입력값이 규칙에 맞지 않습니다." | 아이디(소문자·숫자·_ 4~20), 비밀번호(8~72) 규칙 위반 | 화면의 validate 와 서버 SignupIn 규칙을 맞춘다 |
| 409 "이미 사용 중인 아이디입니다" | 아이디 중복 | 다른 아이디 |
| 남의 글 수정 403 | 정상 동작 (소유권 검사) | - |
| CORS 오류인데 Authorization 헤더가 있는 요청만 실패 | 서버 CORS 의 `allow_headers` 에 Authorization 이 빠짐 | `allow_headers=["*"]` |
| uvicorn: `ModuleNotFoundError: No module named 'jwt'` 또는 `'pwdlib'` | 심화 requirements 를 설치하지 않음 / 기초 과정 가상환경을 켬 | `C:\study\authboard\backend` 의 `.venv` 를 켜고 `pip install -r requirements.txt` |
| uvicorn 시작 시 5434 연결 실패 | 심화 DB(react-auth-db)가 꺼져 있음 | `C:\study\authboard` 에서 `docker compose up -d` |
| `[Errno 10048] ... 8000` (only one usage of each socket address) | 기초 과정 API 서버가 아직 8000 을 쓰는 중 | 그 터미널에서 Ctrl+C |
