from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal

class Payment(models.Model):
    class Status(models.TextChoices):
        CAPTURED = 'captured', _('Captured')
        FAILED = 'failed', _('Failed')
    
    class Method(models.TextChoices):
        PIX = 'pix', _('Pix')
        CARD = 'card', _('Card')

    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text='A unique key to ensure idempotent payment requests.'
    )

    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    platform_fee_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=10,
        choices=Method.choices
    )

    installments = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CAPTURED
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Payment {self.id} - {self.gross_amount} ({self.status})'
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

class LedgerEntry(models.Model):
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='ledger_entries'
    )

    recipient_id = models.CharField(max_length=255)

    role = models.CharField(max_length=50)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.recipient_id} ({self.role}): {self.amount}"
    
class OutboxEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PUBLISHED = 'published', _('Published')
        FAILED = 'failed', _('Failed')

    event_type = models.CharField(max_length=50, default='payment_captured')

    payload = models.JSONField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Event {self.event_type} - {self.status}"