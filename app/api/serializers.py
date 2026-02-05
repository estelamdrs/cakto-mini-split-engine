from rest_framework import serializers
from app.models import Payment, OutboxEvent, LedgerEntry
from decimal import Decimal

# Input Serializers

class SplitInputSerializer(serializers.Serializer):
    recipient_id = serializers.CharField(max_length=100)
    role = serializers.CharField(max_length=50)
    percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0.01,
        max_value=100.00
    )

class PaymentInputSerializers(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01
    )
    currency = serializers.CharField(max_length=3)
    payment_method = serializers.ChoiceField(choices=Payment.Method.choices)
    installments = serializers.IntegerField(min_value=1, default=1)
    splits = serializers.ListField(
        child=SplitInputSerializer(),
        allow_empty=False,
        min_length=1,
        max_length=5,
        help_text="List of splits for the payment."
    )

    def validate_currency(self, value):
        if value.upper() != 'BRL':
            raise serializers.ValidationError("Currency must be 'BRL'.")
        return value.upper()
    
    def validate_splits(self, value):
        total_percent = sum(item['percent'] for item in value)

        if total_percent != Decimal('100.00'):
            raise serializers.ValidationError("Total percent of splits must equal 100%.")
        
        return value
    
# Output Serializers

class ReceivableOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ['recipient_id', 'role', 'amount']

class OutboxOutputSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='event_type')

    class Meta:
        model = OutboxEvent
        fields = ['type', 'status']

class PaymentOutputSerializer(serializers.ModelSerializer):
    payment_id = serializers.CharField(source='id')
    receivables = ReceivableOutputSerializer(many=True, source='ledger_entries')
    outbox_event = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'payment_id',
            'status',
            'gross_amount',
            'platform_fee_amount',
            'net_amount',
            'receivables',
            'outbox_event'
        ]

    def get_outbox_event(self, obj):
        event = self.context.get('outbox_event')
        
        if event:
            return OutboxOutputSerializer(event).data
        
        return None