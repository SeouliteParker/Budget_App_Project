
"""CLI 계층 — 인자 파싱, 대화형 입력, 출력 포맷팅을 담당한다."""
import argparse
import csv
import sys

from .decorators import handle_errors, log_execution, measure_time
from .repository import TransactionRepository, CategoryRepository, BudgetRepository
from .service import TransactionService, BudgetService, CategoryService
from .utils import validate_date, validate_month, validate_amount, validate_type, parse_tags

DEFAULT_CATEGORIES = ["food", "transport", "rent", "etc"]


# ---------------------------------------------------------------------------
# argparse 구성
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="budget_app",
        description="나만의 용돈 기입장 콘솔 프로그램",
    )
    parser.add_argument("--data-dir", default="./data", help="데이터 저장 폴더 (기본값: ./data)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("add", help="거래를 대화형으로 추가한다")

    p_list = sub.add_parser("list", help="거래 목록을 최신순으로 조회한다")
    p_list.add_argument("--limit", type=int, default=10, help="조회할 최대 건수 (기본 10)")

    p_search = sub.add_parser("search", help="조건에 맞는 거래를 검색한다")
    p_search.add_argument("--from", dest="date_from", help="시작일 YYYY-MM-DD")
    p_search.add_argument("--to", dest="date_to", help="종료일 YYYY-MM-DD")
    p_search.add_argument("--category", help="카테고리")
    p_search.add_argument("--type", help="income 또는 expense")
    p_search.add_argument("--q", help="메모 키워드")
    p_search.add_argument("--tag", help="태그")

    p_summary = sub.add_parser("summary", help="월별 요약을 출력한다")
    p_summary.add_argument("--month", required=True, help="YYYY-MM")
    p_summary.add_argument("--top", type=int, default=3, help="지출 TOP N (기본 3)")

    p_delete = sub.add_parser("delete", help="거래를 삭제한다")
    p_delete.add_argument("--id", required=True, help="삭제할 거래 id")

    p_update = sub.add_parser("update", help="거래를 수정한다 (옵션 방식)")
    p_update.add_argument("--id", required=True, help="수정할 거래 id")
    p_update.add_argument("--date")
    p_update.add_argument("--type")
    p_update.add_argument("--category")
    p_update.add_argument("--amount")
    p_update.add_argument("--memo")
    p_update.add_argument("--tags", help="쉼표로 구분된 태그")

    p_budget = sub.add_parser("budget", help="월별 예산을 설정/조회한다")
    budget_sub = p_budget.add_subparsers(dest="budget_cmd", required=True)
    p_bset = budget_sub.add_parser("set", help="예산 설정")
    p_bset.add_argument("--month", required=True)
    p_bset.add_argument("--amount", type=int, required=True)
    p_bget = budget_sub.add_parser("get", help="예산 조회")
    p_bget.add_argument("--month", required=True)

    p_cat = sub.add_parser("category", help="카테고리를 관리한다")
    cat_sub = p_cat.add_subparsers(dest="cat_cmd", required=True)
    cat_sub.add_parser("list", help="카테고리 목록 출력")
    cat_sub.add_parser("add", help="카테고리 추가 (대화형)")
    p_cat_remove = cat_sub.add_parser("remove", help="카테고리 삭제")
    p_cat_remove.add_argument("--name", required=True)

    p_export = sub.add_parser("export", help="거래를 CSV로 내보낸다")
    p_export.add_argument("--out", required=True, help="출력 CSV 경로")
    p_export.add_argument("--month", help="YYYY-MM")
    p_export.add_argument("--from", dest="date_from", help="YYYY-MM-DD")
    p_export.add_argument("--to", dest="date_to", help="YYYY-MM-DD")

    p_import = sub.add_parser("import", help="CSV로부터 거래를 일괄 등록한다")
    p_import.add_argument("--from", dest="csv_path", required=True, help="입력 CSV 경로")

    return parser


# ---------------------------------------------------------------------------
# 대화형 입력 헬퍼
# ---------------------------------------------------------------------------

def prompt_add(cat_service: CategoryService) -> dict:
    date = input("날짜(YYYY-MM-DD): ").strip()
    while True:
        try:
            validate_date(date)
            break
        except ValueError as e:
            print(f"[오류] {e}")
            print("[힌트] 예: 2024-01-15")
            date = input("날짜(YYYY-MM-DD): ").strip()

    type_ = input("타입(income/expense): ").strip()
    while True:
        try:
            validate_type(type_)
            break
        except ValueError as e:
            print(f"[오류] {e}")
            type_ = input("타입(income/expense): ").strip()

    categories = cat_service.list_names()
    category = input("카테고리: ").strip()
    while category not in categories:
        print(f"[안내] 등록되지 않은 카테고리입니다. 현재 목록: {', '.join(categories) if categories else '없음'}")
        category = input("카테고리: ").strip()

    amount = input("금액(양수): ").strip()
    while True:
        try:
            validate_amount(amount)
            break
        except ValueError as e:
            print(f"[오류] {e}")
            amount = input("금액(양수): ").strip()

    memo = input("메모(선택): ").strip() or None
    tags_raw = input("태그(쉼표로 구분, 없으면 엔터): ").strip()
    tags = parse_tags(tags_raw)

    return dict(date=date, type_=type_, category=category, amount=amount, memo=memo, tags=tags)


def prompt_category_name() -> str:
    return input("카테고리명: ").strip()


# ---------------------------------------------------------------------------
# 명령별 실행 함수 (각각 데코레이터로 예외/로그/시간측정 적용)
# ---------------------------------------------------------------------------

@handle_errors
@log_execution
@measure_time
def cmd_add(args, tx_service: TransactionService, cat_service: CategoryService):
    fields = prompt_add(cat_service)
    tx = tx_service.add(**fields)
    print(f"[저장 완료] id={tx.id}")


@handle_errors
@log_execution
@measure_time
def cmd_list(args, tx_service: TransactionService):
    txs = tx_service.list_recent(limit=args.limit)
    if not txs:
        print("[안내] 등록된 거래가 없습니다.")
        return
    for tx in txs:
        memo = tx.memo or ""
        print(f"{tx.id} | {tx.date} | {tx.type:<7} | {tx.category:<10} | {tx.amount:>10} | {memo}")


@handle_errors
@log_execution
@measure_time
def cmd_search(args, tx_service: TransactionService):
    results = tx_service.search(
        date_from=args.date_from,
        date_to=args.date_to,
        category=args.category,
        type_=args.type,
        keyword=args.q,
        tag=args.tag,
    )
    if not results:
        print("[안내] 조건에 맞는 거래가 없습니다.")
        return
    for tx in results:
        memo = tx.memo or ""
        print(f"{tx.id} | {tx.date} | {tx.type:<7} | {tx.category:<10} | {tx.amount:>10} | {memo}")


@handle_errors
@log_execution
@measure_time
def cmd_summary(args, tx_service: TransactionService, budget_service: BudgetService):
    validate_month(args.month)
    result = tx_service.summary(args.month, top_n=args.top)
    if not result["found"]:
        print(f"[안내] {args.month} 데이터 없음")
        return

    print(f"총 수입: {result['income']}원")
    print(f"총 지출: {result['expense']}원")
    print(f"잔액: {result['balance']}원")

    usage = budget_service.get_usage(args.month, result["expense"])
    if usage:
        print(f"예산: {usage['amount']}원 (사용률 {usage['usage_rate']:.1f}%)")
        if usage["over"]:
            print("⚠ 예산을 초과했습니다!")

    if result["top_categories"]:
        print(f"\n지출 TOP {args.top}")
        for i, (cat, total) in enumerate(result["top_categories"], start=1):
            print(f"{i}) {cat} {total}원")


@handle_errors
@log_execution
@measure_time
def cmd_delete(args, tx_service: TransactionService):
    ok = tx_service.delete(args.id)
    if ok:
        print(f"[삭제 완료] id={args.id}")
    else:
        print(f"[오류] 존재하지 않는 id입니다: {args.id}")
        sys.exit(1)


@handle_errors
@log_execution
@measure_time
def cmd_update(args, tx_service: TransactionService):
    changes = dict(
        date=args.date,
        type=args.type,
        category=args.category,
        amount=args.amount,
        memo=args.memo,
        tags=args.tags,
    )
    ok = tx_service.update(args.id, **changes)
    if ok:
        print(f"[수정 완료] id={args.id}")
    else:
        print(f"[오류] 존재하지 않는 id입니다: {args.id}")
        sys.exit(1)


@handle_errors
@log_execution
@measure_time
def cmd_budget_set(args, budget_service: BudgetService):
    validate_month(args.month)
    if args.amount <= 0:
        raise ValueError("예산은 0보다 큰 양수여야 합니다.")
    budget_service.set_budget(args.month, args.amount)
    print(f"[저장 완료] {args.month} 예산 {args.amount}원")


@handle_errors
@log_execution
@measure_time
def cmd_budget_get(args, budget_service: BudgetService):
    validate_month(args.month)
    amount = budget_service.budget_repo.get(args.month)
    if amount is None:
        print(f"[안내] {args.month} 예산이 설정되어 있지 않습니다.")
    else:
        print(f"{args.month} 예산: {amount}원")


@handle_errors
@log_execution
@measure_time
def cmd_category(args, cat_service: CategoryService):
    if args.cat_cmd == "list":
        names = cat_service.list_names()
        if not names:
            print("[안내] 등록된 카테고리가 없습니다.")
        for name in names:
            print(f"- {name}")
    elif args.cat_cmd == "add":
        name = prompt_category_name()
        cat_service.add(name)
        print(f"[저장 완료] category={name}")
    elif args.cat_cmd == "remove":
        cat_service.remove(args.name)
        print(f"[삭제 완료] category={args.name}")


@handle_errors
@log_execution
@measure_time
def cmd_export(args, tx_service: TransactionService):
    if not args.month and not (args.date_from and args.date_to):
        raise ValueError("export는 --month 또는 --from/--to 조건이 필요합니다.")

    if args.month:
        validate_month(args.month)
        results = [tx for tx in tx_service.tx_repo.stream_all() if tx.date.startswith(args.month)]
        results.sort(key=lambda t: (t.date, t.id), reverse=True)
    else:
        results = tx_service.search(date_from=args.date_from, date_to=args.date_to)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "type", "category", "amount", "memo", "tags"])
        for tx in results:
            writer.writerow([tx.date, tx.type, tx.category, tx.amount, tx.memo or "", ",".join(tx.tags)])

    print(f"[완료] {args.out} ({len(results)} records)")


@handle_errors
@log_execution
@measure_time
def cmd_import(args, tx_service: TransactionService):
    imported, skipped = 0, 0
    try:
        with open(args.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    tx_service.add(
                        date=row["date"],
                        type_=row["type"],
                        category=row["category"],
                        amount=row["amount"],
                        memo=(row.get("memo") or None),
                        tags=parse_tags(row.get("tags", "")),
                    )
                    imported += 1
                except (ValueError, KeyError):
                    skipped += 1
    except FileNotFoundError:
        raise ValueError(f"CSV 파일을 찾을 수 없습니다: {args.csv_path}")

    print(f"[완료] imported={imported}, skipped={skipped}")


# ---------------------------------------------------------------------------
# 조립 및 실행
# ---------------------------------------------------------------------------

def dispatch(args, tx_service, budget_service, cat_service):
    if args.command == "add":
        cmd_add(args, tx_service, cat_service)
    elif args.command == "list":
        cmd_list(args, tx_service)
    elif args.command == "search":
        cmd_search(args, tx_service)
    elif args.command == "summary":
        cmd_summary(args, tx_service, budget_service)
    elif args.command == "delete":
        cmd_delete(args, tx_service)
    elif args.command == "update":
        cmd_update(args, tx_service)
    elif args.command == "budget":
        if args.budget_cmd == "set":
            cmd_budget_set(args, budget_service)
        elif args.budget_cmd == "get":
            cmd_budget_get(args, budget_service)
    elif args.command == "category":
        cmd_category(args, cat_service)
    elif args.command == "export":
        cmd_export(args, tx_service)
    elif args.command == "import":
        cmd_import(args, tx_service)
    else:
        raise ValueError(f"알 수 없는 명령입니다: {args.command}")


def main():
    parser = build_parser()
    args = parser.parse_args()

    tx_repo = TransactionRepository(f"{args.data_dir}/transactions.jsonl")
    cat_repo = CategoryRepository(f"{args.data_dir}/categories.jsonl")
    budget_repo = BudgetRepository(f"{args.data_dir}/budgets.jsonl")

    if not cat_repo.list_names():
        for name in DEFAULT_CATEGORIES:
            cat_repo.add(name)
        print(f"[안내] 카테고리가 비어 있어 기본 카테고리를 생성했습니다: {', '.join(DEFAULT_CATEGORIES)}")

    tx_service = TransactionService(tx_repo, cat_repo)
    budget_service = BudgetService(budget_repo)
    cat_service = CategoryService(cat_repo, tx_repo)

    dispatch(args, tx_service, budget_service, cat_service)
    sys.exit(0)