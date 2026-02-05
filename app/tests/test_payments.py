from django.test import TestCase
from app.services.split_calculator import SplitCalculator
from decimal import Decimal
from rest_framework.test import APITestCase
from django.urls import reverse
from app.models import Payment, OutboxEvent, LedgerEntry
from rest_framework import status

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

class PaymentIntegrationTests(APITestCase):
    def setUp(self):
        self.url = reverse('create-payment')
        self.valid_payload = {
            "amount": "297.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 3,
            "splits": [
                { "recipient_id": "producer_1", "role": "producer", "percent": 70 },
                { "recipient_id": "affiliate_9", "role": "affiliate", "percent": 30 }
            ]
        }
        self.headers = {'HTTP_IDEMPOTENCY_KEY': 'abc-123-unique'}

    def test_create_payment_success(self):
        response = self.client.post(self.url, self.valid_payload, format='json', **self.headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(LedgerEntry.objects.count(), 2)
        self.assertEqual(OutboxEvent.objects.count(), 1)

        payment = Payment.objects.first()
        self.assertEqual(payment.gross_amount, Decimal('297.00'))
        self.assertEqual(payment.status, 'captured')

    def test_idempotency_same_payload(self):
        self.client.post(self.url, self.valid_payload, format='json', **self.headers)
        response = self.client.post(self.url, self.valid_payload, format='json', **self.headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(str(response.data['gross_amount']), "297.00")

    def test_idempotency_conflict(self):
        self.client.post(self.url, self.valid_payload, format='json', **self.headers)

        payload_fake = self.valid_payload.copy()
        payload_fake['amount'] = "500.00"

        response = self.client.post(self.url, payload_fake, format='json', **self.headers)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)