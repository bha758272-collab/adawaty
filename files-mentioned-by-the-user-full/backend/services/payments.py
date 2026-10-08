"""Payment integration boundary.

Keep provider credentials server-side. Premium pages deliberately do not invoke
this module until a provider, prices, webhook verification and entitlement
rules are configured.
"""
import os

class PaymentNotConfigured(RuntimeError):
    pass

def create_checkout_session(*args, **kwargs):
    if not os.getenv("STRIPE_SECRET_KEY"):
        raise PaymentNotConfigured("بوابة الدفع غير مهيأة بعد.")
    # Add the payment-provider SDK and verified webhook handling at launch.
    raise PaymentNotConfigured("لم يتم تفعيل الاشتراكات بعد.")
