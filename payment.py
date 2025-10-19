import stripe
from config import STRIPE_API_KEY

stripe.api_key = STRIPE_API_KEY

class PaymentProcessor:
    @staticmethod
    def create_payment_intent(amount, currency='brl'):
        try:
            # Converter para centavos (Stripe trabalha com valores inteiros)
            amount_in_cents = int(amount * 100)
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency,
                payment_method_types=['card'],
            )
            
            return {
                'success': True,
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'amount': amount
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def confirm_payment(payment_intent_id):
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return payment_intent.status == 'succeeded'
        except:
            return False
