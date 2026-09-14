"""비즈니스 로직 계층 — 저장소를 조합해 실제 기능을 구현한다."""
from typing import Iterator, Optional

from .models import Transaction
from .repository import TransactionRepository, CategoryRepository, BudgetRepository
from .utils import validate_date, validate_amount, validate_type


class TransactionService:
    def __init__(self, tx_repo: TransactionRepository, cat_repo: CategoryRepository):
        self.tx_repo = tx_repo
        self.cat_repo = cat_repo

    def add(
        self,
        date: str,
        type_: str,
        category: str,
        amount: str,
        memo: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Transaction:
        validate_date(date)
        validate_type(type_)
        amount_val = validate_amount(amount)

        categories = self.cat_repo.list_names()
        if category not in categories:
            raise ValueError(
                f"등록되지 않은 카테고리입니다: {category} "
                f"(등록된 카테고리: {', '.join(categories) if categories else '없음'})"
            )

        tx_id = self.tx_repo.next_id()
        tx = Transaction(
            id=tx_id,
            type=type_,
            date=date,
            amount=amount_val,
            category=category,
            memo=memo,
            tags=tags or [],
        )
        self.tx_repo.append(tx)
        return tx

import heapq

def list_recent(self, limit: int = 10) -> list[Transaction]:
    return heapq.nlargest(
        limit,
        self.tx_repo.stream_all(),
        key=lambda t: (t.date, t.id)
    )

def search(
    self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        category: Optional[str] = None,
        type_: Optional[str] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> list[Transaction]:
        """조건에 맞는 거래를 제너레이터로 필터링한 뒤 최신순으로 반환한다."""

        def _filtered() -> Iterator[Transaction]:
            for tx in self.tx_repo.stream_all():
                if date_from and tx.date < date_from:
                    continue
                if date_to and tx.date > date_to:
                    continue
                if category and tx.category != category:
                    continue
                if type_ and tx.type != type_:
                    continue
                if keyword and (not tx.memo or keyword not in tx.memo):
                    continue
                if tag and tag not in tx.tags:
                    continue
                yield tx

        results = list(_filtered())
        results.sort(key=lambda t: (t.date, t.id), reverse=True)
        return results

    def delete(self, tx_id: str) -> bool:
        all_tx = list(self.tx_repo.stream_all())
        filtered = [t for t in all_tx if t.id != tx_id]
        if len(filtered) == len(all_tx):
            return False
        self.tx_repo.rewrite_all(filtered)
        return True

    def update(self, tx_id: str, **changes) -> bool:
        """changes에 담긴 값(None이 아닌 것만) 으로 해당 id의 필드를 갱신한다."""
        if "date" in changes and changes["date"] is not None:
            validate_date(changes["date"])
        if "type" in changes and changes["type"] is not None:
            validate_type(changes["type"])
        if "amount" in changes and changes["amount"] is not None:
            changes["amount"] = validate_amount(changes["amount"])
        if "category" in changes and changes["category"] is not None:
            if changes["category"] not in self.cat_repo.list_names():
                raise ValueError(f"등록되지 않은 카테고리입니다: {changes['category']}")
        if "tags" in changes and isinstance(changes["tags"], str):
            changes["tags"] = [t.strip() for t in changes["tags"].split(",") if t.strip()]

        all_tx = list(self.tx_repo.stream_all())
        found = False
        for tx in all_tx:
            if tx.id == tx_id:
                found = True
                for key, value in changes.items():
                    if value is not None:
                        setattr(tx, key, value)
        if not found:
            return False
        self.tx_repo.rewrite_all(all_tx)
        return True

    def summary(self, month: str, top_n: int = 3) -> dict:
        income_total = 0
        expense_total = 0
        category_totals: dict[str, int] = {}
        found_any = False

        for tx in self.tx_repo.stream_all():
            if not tx.date.startswith(month):
                continue
            found_any = True
            if tx.type == "income":
                income_total += tx.amount
            else:
                expense_total += tx.amount
                category_totals[tx.category] = category_totals.get(tx.category, 0) + tx.amount

        if not found_any:
            return {"found": False}

        top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]

        return {
            "found": True,
            "income": income_total,
            "expense": expense_total,
            "balance": income_total - expense_total,
            "top_categories": top_categories,
        }


class BudgetService:
    def __init__(self, budget_repo: BudgetRepository):
        self.budget_repo = budget_repo

    def set_budget(self, month: str, amount: int) -> None:
        self.budget_repo.upsert(month, amount)

    def get_usage(self, month: str, expense_total: int) -> Optional[dict]:
        amount = self.budget_repo.get(month)
        if amount is None:
            return None
        usage_rate = (expense_total / amount) * 100 if amount > 0 else 0.0
        return {
            "amount": amount,
            "usage_rate": usage_rate,
            "over": expense_total > amount,
        }


class CategoryService:
    def __init__(self, cat_repo: CategoryRepository, tx_repo: TransactionRepository):
        self.cat_repo = cat_repo
        self.tx_repo = tx_repo

    def list_names(self) -> list[str]:
        return self.cat_repo.list_names()

    def add(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("카테고리 이름이 비어 있습니다.")
        if name in self.cat_repo.list_names():
            raise ValueError(f"이미 존재하는 카테고리입니다: {name}")
        self.cat_repo.add(name)

    def remove(self, name: str) -> None:
        in_use = any(tx.category == name for tx in self.tx_repo.stream_all())
        if in_use:
            raise ValueError(
                f"'{name}' 카테고리를 사용 중인 거래가 있어 삭제할 수 없습니다. "
                f"먼저 해당 거래를 수정하거나 삭제해주세요."
            )
        removed = self.cat_repo.remove(name)
        if not removed:
            raise ValueError(f"존재하지 않는 카테고리입니다: {name}")
