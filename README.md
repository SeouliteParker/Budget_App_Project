# 나만의 용돈 기입장 (budget_app)

Python 표준 라이브러리만으로 구현한 콘솔 가계부 프로그램입니다.

## 1. 실행 방법

- 요구 사항: Python 3.10 이상 (외부 라이브러리 설치 불필요)
- 프로젝트 루트(이 README가 있는 폴더)에서 실행합니다.

```bash
python -m budget_app --help
python -m budget_app add
python -m budget_app list --limit 5
python -m budget_app summary --month 2024-01
```

기본 데이터 폴더는 `./data`이며, `--data-dir` 옵션으로 변경할 수 있습니다.

```bash
python -m budget_app --data-dir ./my-data list
```

## 2. 저장 파일 위치/형식

- 저장 폴더: `./data` (기본값, `--data-dir`로 변경 가능)
- 저장 포맷: **JSONL** (한 줄에 거래/카테고리/예산 1건씩 JSON으로 저장)
- 저장 파일 3종:
  - `data/transactions.jsonl` — 거래 내역
  - `data/categories.jsonl` — 카테고리 목록
  - `data/budgets.jsonl` — 월별 예산
- 최초 실행 시 `categories.jsonl`이 비어 있으면 기본 카테고리(`food, transport, rent, etc`)를 자동 생성합니다.
- 거래 수정(`update`)/삭제(`delete`)/카테고리 삭제는 임시 파일에 쓴 뒤 `os.replace()`로 **원자적 교체**하여 중간에 오류가 나도 기존 파일이 손상되지 않도록 처리했습니다.

## 3. 주요 명령 예시

### 거래 추가 (대화형)
```
$ python -m budget_app add
날짜(YYYY-MM-DD): 2024-01-15
타입(income/expense): expense
카테고리: food
금액(양수): 15000
메모(선택): 점심
태그(쉼표로 구분, 없으면 엔터): meal
[저장 완료] id=TX-000001
```

### 목록 조회
```
$ python -m budget_app list --limit 3
```

### 검색
```
$ python -m budget_app search --category food --from 2024-01-01 --to 2024-01-31
$ python -m budget_app search --type expense --q 점심 --tag meal
```

### 월별 요약
```
$ python -m budget_app summary --month 2024-01 --top 3
```

### 예산 설정
```
$ python -m budget_app budget set --month 2024-01 --amount 500000
```
`summary` 실행 시 예산이 설정되어 있으면 사용률(%)과 초과 여부를 함께 보여줍니다.

### 카테고리 관리
```
$ python -m budget_app category list
$ python -m budget_app category add
$ python -m budget_app category remove --name etc
```
사용 중인(거래가 존재하는) 카테고리는 삭제가 거부됩니다.

### 거래 수정 (옵션 방식으로 고정)
```
$ python -m budget_app update --id TX-000001 --amount 20000 --memo "점심(수정)"
```
수정할 필드만 옵션으로 전달하면 되며, 전달하지 않은 필드는 기존 값을 유지합니다.

### 거래 삭제
```
$ python -m budget_app delete --id TX-000001
```

### CSV 내보내기 / 가져오기
```
$ python -m budget_app export --out export.csv --month 2024-01
$ python -m budget_app import --from import.csv
```
`export`는 `--month` 또는 `--from`/`--to` 중 하나 이상의 조건이 반드시 필요합니다.

## 4. import/export CSV 스키마

| column   | required | 설명 |
|----------|----------|------|
| date     | Y        | YYYY-MM-DD |
| type     | Y        | income / expense |
| category | Y        | 등록된 카테고리 |
| amount   | Y        | 양수 정수 |
| memo     | N        | 문자열 |
| tags     | N        | 쉼표(,)로 구분된 문자열 |

- 인코딩: UTF-8, 첫 줄은 헤더 포함
- `import` 시 등록되지 않은 카테고리이거나 값이 유효하지 않은 행은 건너뛰고(`skipped`) 계속 진행합니다.

## 5. 구조 (모듈 분리)

```
budget_app/
├── __main__.py    # 진입점 (python -m budget_app)
├── cli.py         # argparse 명령 정의, 대화형 입력, 출력 포맷
├── service.py     # 비즈니스 로직 (검증, CRUD, 요약, 예산 계산)
├── repository.py  # 파일 I/O 전담 (JSONL 스트리밍 읽기/원자적 쓰기)
├── models.py      # Transaction / Budget / Category dataclass
├── decorators.py  # 예외 처리 / 실행 로그 / 실행 시간 측정 데코레이터
└── utils.py       # 날짜/금액/타입 검증 유틸
```

- **모델(models.py)**: 데이터 구조만 정의, 로직 없음
- **저장소(repository.py)**: 파일 읽기/쓰기만 담당. `stream_all()`은 제너레이터로 파일을 한 줄씩 읽어 대용량 파일도 메모리 부담 없이 처리
- **서비스(service.py)**: 저장소를 조합해 실제 기능(add/search/summary/budget 등) 구현, 입력 검증 수행
- **CLI(cli.py)**: 인자 파싱 → 서비스 호출 → 결과 출력만 담당

## 6. 오류 처리

- 모든 예외는 스택트레이스 대신 `[오류] 원인` + `[힌트] 해결 방법` 형태로 출력합니다.
- 정상 종료 시 exit code `0`, 오류 발생 시 `0`이 아닌 값으로 종료합니다.
