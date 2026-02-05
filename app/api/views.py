from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.models import Payment, LedgerEntry, OutboxEvent
from app.api.serializers import (
    PaymentInputSerializer, 
    PaymentOutputSerializer
)
from app.services.split_calculator import SplitCalculator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

class PaymentCreateView(APIView):
    def post(self, request):
        idempotency_key = request.headers.get('Idempotency-Key')

        if not idempotency_key:
            return Response(
                {"error": "Idempotency-Key header is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        existing_payment = Payment.objects.filter(idempotency_key=idempotency_key).first()

        if existing_payment:
            input_amount = request.data.get('amount')

            if str(existing_payment.gross_amount) != str(input_amount):
                return Response(
                    {"error": "Amount mismatch for idempotent request."},
                    status=status.HTTP_409_CONFLICT
                )
            
            original_event = OutboxEvent.objects.filter(
                payload__payment_id=existing_payment.id
            ).first()

            serializer = PaymentOutputSerializer(
                existing_payment,
                context={'outbox_event': original_event}
            )

            return Response(serializer.data, status=status.HTTP_200_OK)
        
        input_serializer = PaymentInputSerializer(data=request.data)

        if not input_serializer.is_valid():
            return Response(
                input_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_data = input_serializer.validated_data

        try:
            calculation_result = SplitCalculator.calculate(
                amount=valid_data['amount'],
                payment_method=valid_data['payment_method'],
                installments=valid_data['installments'],
                splits=valid_data['splits']
            )
        except DjangoValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                payment = Payment.objects.create(
                    idempotency_key=idempotency_key,
                    gross_amount=calculation_result['gross_amount'],
                    platform_fee_amount=calculation_result['platform_fee_amount'],
                    net_amount=calculation_result['net_amount'],
                    payment_method=valid_data['payment_method'],
                    installments=valid_data['installments'],
                    status=Payment.Status.CAPTURED
                )

                ledger_entries = []

                for entry in calculation_result['receivables']:
                    ledger_entries.append(LedgerEntry(
                        payment=payment,
                        recipient_id=entry['recipient_id'],
                        role=entry['role'],
                        amount=entry['amount']
                    ))
                
                LedgerEntry.objects.bulk_create(ledger_entries)

                output_payload = PaymentOutputSerializer(payment).data

                output_payload['receivables'] = calculation_result['receivables']

                outbox_event = OutboxEvent.objects.create(
                    event_type='payment_captured',
                    payload=output_payload,
                    status=OutboxEvent.Status.PENDING
                )

        except Exception as e:
            return Response(
                {"error": "An error occurred while processing the payment."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        final_serializer = PaymentOutputSerializer(
            payment,
            context={'outbox_event': outbox_event}
        )

        return Response(final_serializer.data, status=status.HTTP_201_CREATED)

