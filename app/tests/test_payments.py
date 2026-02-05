from django.test import TestCase
from app.services.split_calculator import SplitCalculator
from decimal import Decimal

class SplitCalculatorUnitTests(TestCase):
    def test_pix_zero_fee(self):
        result = SplitCalculator.calculate(
            amount=Decimal('100.00'),
            payment_method='pix',
            installments=1,
            splits=[{'recipient_id': '1', 'role': 'dev', 'percent': 100}]
        )

        self.assertEqual(result['platform_fee_amount'], Decimal('0.00'))
        self.assertEqual(result['net_amount'], Decimal('100.00'))
        self.assertEqual(result['receivables'][0]['amount'], Decimal('100.00'))

    def test_card_tax_logic_3x(self):
        result = SplitCalculator.calculate(
            amount=Decimal('100.00'),
            payment_method='card',
            installments=3,
            splits=[{'recipient_id': '1', 'role': 'dev', 'percent': 100}]
        )

        self.assertEqual(result['platform_fee_amount'], Decimal('8.99'))
        self.assertEqual(result['net_amount'], Decimal('91.01'))

    def test_penny_allocation_rounding(self):
        result = SplitCalculator.calculate(
            amount=Decimal('100.00'),
            payment_method='pix',
            installments=1,
            splits=[
                {'recipient_id': 'A', 'role': 'r', 'percent': 33.33},
                {'recipient_id': 'B', 'role': 'r', 'percent': 33.33},
                {'recipient_id': 'C', 'role': 'r', 'percent': 33.34}, 
            ]
        )
        
        receivables = result['receivables']
        total_rec = sum(r['amount'] for r in receivables)
        self.assertEqual(total_rec, Decimal('100.00'))

    def test_rounding_remainder_logic(self):
        result = SplitCalculator.calculate(
            amount=Decimal('0.05'),
            payment_method='pix',
            installments=1,
            splits=[
                {'recipient_id': 'A', 'role': 'r', 'percent': 50},
                {'recipient_id': 'B', 'role': 'r', 'percent': 50},
            ]
        )

        r1 = result['receivables'][0]['amount']
        r2 = result['receivables'][1]['amount']

        self.assertEqual(r1, Decimal('0.02'))
        self.assertEqual(r2, Decimal('0.03'))
        self.assertEqual(r1 + r2, Decimal('0.05'))