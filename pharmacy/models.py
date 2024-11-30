from django.contrib.auth.models import AbstractUser
from django.db import models

class customuser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('customer', 'Customer'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')


class Medicine(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    image = models.ImageField(upload_to='medicines/', null=True, blank=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=15)
    customer_address = models.TextField()
    quantity = models.PositiveIntegerField()
    order_date = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(customuser, null=True, blank=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Canceled', 'Canceled')],
        default='Pending'
    )
    checkout_request_id = models.CharField(max_length=255, null=True, blank=True)  # Added field for M-Pesa CheckoutRequestID


    def __str__(self):
        return f"Order for {self.medicine.name} by {self.customer_name}"

class Cart(models.Model):
    user = models.OneToOneField(customuser, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True, unique=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"Cart for user: {self.user.username}"
        return f"Cart for session: {self.session_id}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self):
        return self.medicine.price * self.quantity
    

class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(
        max_length=20, 
        choices=[('Success', 'Success'), ('Failed', 'Failed'), ('Canceled', 'Canceled')],
    )
    payment_method = models.CharField(
        max_length=50, 
        choices=[('M-Pesa', 'M-Pesa'), ('CreditCard', 'CreditCard')]
    )
    transaction_id = models.CharField(max_length=100, unique=True)  # Unique transaction ID from the payment provider
    response_code = models.CharField(max_length=10)
    response_description = models.CharField(max_length=255)
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Order {self.order.id} - {self.payment_status}"


