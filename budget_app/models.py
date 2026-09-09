"""데이터 모델 정의 (dataclass 기반)"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Transaction:
    """거래 내역 모델"""
    id: str
    type: str            # "income" | "expense"
    date: str             # "YYYY-MM-DD"
    amount: int            # 양수
    category: str
    memo: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "date": self.date,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": self.tags,
        }

    @staticmethod
    def from_dict(d: dict) -> "Transaction":
        return Transaction(
            id=d["id"],
            type=d["type"],
            date=d["date"],
            amount=int(d["amount"]),
            category=d["category"],
            memo=d.get("memo"),
            tags=d.get("tags") or [],
        )


@dataclass
class Budget:
    """월별 예산 모델"""
    month: str   # "YYYY-MM"
    amount: int

    def to_dict(self) -> dict:
        return {"month": self.month, "amount": self.amount}

    @staticmethod
    def from_dict(d: dict) -> "Budget":
        return Budget(month=d["month"], amount=int(d["amount"]))


@dataclass
class Category:
    """카테고리 모델"""
    name: str

    def to_dict(self) -> dict:
        return {"name": self.name}

    @staticmethod
    def from_dict(d: dict) -> "Category":
        return Category(name=d["name"])
