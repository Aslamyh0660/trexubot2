from __future__ import annotations

from ..config import Settings, VIPPlan


class PaymentService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_plan(self, code: str) -> VIPPlan | None:
        return self.settings.vip_plans.get(code)

    def format_bank_details(self, plan: VIPPlan, lang: str = 'fa') -> str:
        title = plan.title_fa if lang == 'fa' else plan.title_en
        return (
            f'پلن: {title}\n'
            f'مبلغ: {plan.price:,} تومان\n'
            f'شماره کارت: {self.settings.bank_card_number}\n'
            f'به نام: {self.settings.bank_card_holder}'
        )
