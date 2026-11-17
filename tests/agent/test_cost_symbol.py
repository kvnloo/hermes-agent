"""Cost label behavior for display-symbol customization (PR #156783)."""

from decimal import Decimal

from agent import usage_pricing


def test_cost_labels_follow_custom_currency_symbol(monkeypatch):
    monkeypatch.setattr(usage_pricing, "CURRENCY_SYMBOL", "¥", raising=False)

    amounts = (Decimal("0"), Decimal("0.0046"), Decimal("0.00005"), Decimal("1.23"))
    assert [usage_pricing.format_cost_label(amount) for amount in amounts] == [
        "¥0.00",
        "~¥0.0046",
        "~¥<0.0001",
        "~¥1.23",
    ]
