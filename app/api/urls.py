from django.urls import path
from app.api.views import PaymentCreateView

urlpatterns = [
    path('payments', PaymentCreateView.as_view(), name='create-payment'),
]