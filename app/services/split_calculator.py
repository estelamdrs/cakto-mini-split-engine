from decimal import Decimal
from django.core.exceptions import ValidationError

class SplitCalculator:
    @staticmethod
    def calculate(amount: Decimal, payment_method: str, installments: int, splits: list) -> dict:
        fee_percent = SplitCalculator._get_platform_fee_percent(payment_method, installments)
        platform_fee = (amount * fee_percent / 100).quantize(Decimal('0.01'))
        net_amount = amount - platform_fee

        if net_amount <= 0:
            raise ValidationError("Net amount after platform fee must be greater than zero.")
        
        receivables = []
        total_distributed = Decimal('0.00')

        for index, split in enumerate(splits):
            percent = Decimal(str(split['percent']))
            recipient_id = split['recipient_id']
            role = split['role']
            is_last = (index == len(splits) - 1)

            if is_last:
                recipient_amount = net_amount - total_distributed
            else:
                raw_amount = net_amount * (percent / 100)
                recipient_amount = raw_amount.quantize(Decimal('0.01'), rounding='ROUND_DOWN')

            receivables.append({
                'recipient_id': recipient_id,
                'role': role,
                'amount': recipient_amount
            })

            total_distributed += recipient_amount

        if total_distributed != net_amount:
            raise ValidationError("Distributed amount does not equal net amount after platform fee.")
        
        return {
            'gross_amount': amount,
            'platform_fee_amount': platform_fee,
            'net_amount': net_amount,
            'receivables': receivables
        }
    
    @staticmethod
    def _get_platform_fee_percent(method: str, installments: int) -> Decimal:
        if method == 'pix':
            if installments > 1:
                raise ValidationError("PIX payments cannot have installments.")
            return Decimal('0.00')
        
        if method == 'card':
            if not (1 <= installments <= 12):
                raise ValidationError("Card payments must have installments between 1 and 12.")
            
            if installments == 1:
                return Decimal('3.99')
            else:
                additional_rate = (installments - 1) * 2
                return Decimal('4.99') + Decimal(additional_rate)
            
        raise ValidationError(f"{method}: Unsupported payment method.")