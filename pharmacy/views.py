from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.auth.models import User
from .models import Medicine, Order, Cart, CartItem
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
#mpesa imports
import requests
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64
from django.http import HttpResponse


from django.core.mail import send_mail
from django.http import JsonResponse



def home(request):
     medicines = Medicine.objects.all()
     return render(request, 'home.html', {'medicines': medicines})

def order_medicine(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)

    if request.method == "POST":
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        customer_address = request.POST.get('customer_address', '').strip()

        try:
            quantity = int(request.POST.get('quantity', 0))
        except ValueError:
            print("Conversion failed")
            return render(request,'order.html',{
                'medicine': medicine,
                'error':'Please enter a valid quantity',
            })

        if not customer_name or not customer_phone or not customer_address:
            return render(request, 'order.html', {'medicine': medicine, 'error': 'All fields are required.'})

        if quantity <= 0 or quantity > medicine.stock:
            return render(request, 'order.html', {'medicine': medicine, 'error': 'Invalid quantity or insufficient stock.'})

        print("start of process")
        # Create the order
        with transaction.atomic():
            try:
                # Create the Order instance without saving to the database
                order = Order(
                    medicine=medicine,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    customer_address=customer_address,
                    quantity=quantity,
                )

                # Debugging: Print the instance details before saving
                print(f'Order instance before save: {order}')

                # Save the instance to the database
                order.save()

                # Debugging: Confirm successful save
                print("Order successfully saved.")
                print("final quantity after order transaction", quantity)

            except Exception as e:
                # Log the error if the save fails
                print(f'Failed to save order: {e}')
                raise


            # Update stock
            medicine.stock -= quantity
            medicine.save()

            # Add to the user's cart
            user = request.user
            print(user)
            # Get or create the cart for the user (if it doesn't exist)
            cart, _ = Cart.objects.get_or_create(user=user)

            print(cart)

            try:
                # Try to get existing cart item
                cart_item = CartItem.objects.get(cart=cart, medicine=medicine)
                # Update existing cart item quantity
                cart_item.quantity += quantity
            except CartItem.DoesNotExist:
                # Create new cart item with quantity
                 cart_item = CartItem(cart=cart, medicine=medicine, quantity=quantity)

            # Debug: print out what will be saved in the CartItem
            print(f"Saving CartItem: {cart_item}")
            print(f"Cart Item Details: Cart ID: {cart_item.cart.id}, Medicine ID: {cart_item.medicine.id}, Quantity: {cart_item.quantity}")

            # Save the cart item
            cart_item.save()

        messages.success(request, "Order placed successfully!")
        return redirect('pharmacy:cart')

    return render(request, 'order.html', {'medicine': medicine})


def add_to_cart(request, medicine_id):
    medicine = get_object_or_404(Medicine, pk=medicine_id)
    user = request.user

    # Create or retrieve the user's cart
    cart, created = Cart.objects.get_or_create(user=user)

    # Check if the item is already in the cart
    cart_item, created = CartItem.objects.get_or_create(cart=cart, medicine=medicine)

    # Increment quantity if it already exists
    if not created:
        cart_item.quantity += 1
    cart_item.save()

    messages.success(request, f"{medicine.name} added to your cart!")
    return redirect("pharmacy:cart")


def cart(request):
    cart = Cart.objects.filter(user=request.user).first()
    items = cart.items.all() if cart else []
    total_price = sum(item.total_price() for item in items)
    return render(request, "cart.html", {"items": items, "total_price":total_price})

def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    quantity = int(request.POST.get("quantity", 0))
    
    if quantity > 0:
        cart_item.quantity = quantity
        cart_item.save()
    else:
        cart_item.delete()

    messages.success(request, "Cart updated successfully!")
    return redirect("pharmacy:cart")

def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart!")
    return redirect("pharmacy:cart")


def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    items = CartItem.objects.filter(cart=cart) if cart else []
    total_price = sum(item.quantity * item.medicine.price for item in items)

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        customer_email = request.POST.get('customer_email')
        customer_address = request.POST.get('customer_address')
        phone_number = request.POST.get('phone_number')  # Get phone number from form input

        # M-Pesa credentials
        consumer_key = 'qGGvcCbvDKwX1h5S95vPy7gBKaI43xjg9jCzY5iMoGnxZ5G5'
        consumer_secret = '9Q12LudJh8NLnMmgoMGjGPDXgJtniWDrXMj7y6xBuN0dpAQOBRGlV5e6XUJCWrAn'
        #api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        business_shortcode = '174379'  # Replace with your Paybill or Till number
        passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919' 
        callback_url = 'https://shining-rabbit-uniquely.ngrok-free.app/tenant/payments/response'  # Replace with your callback URL

        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode((business_shortcode + passkey + timestamp).encode()).decode()

        # Get access token
        auth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        auth_response = requests.get(auth_url, auth=(consumer_key, consumer_secret))
        access_token = auth_response.json().get('access_token')

         # Convert Decimal to float
        total_price_float = float(total_price)

        # Prepare STK push payload
        stk_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        headers = {'Authorization': f'Bearer {access_token}'}
        payload = {
            "BusinessShortCode": business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": total_price_float,
            "PartyA": phone_number,
            "PartyB": business_shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": "MEDIVANA",
            "TransactionDesc": "Medicine Purchase"
        }

        # Send STK push request
        stk_response = requests.post(stk_url, headers=headers, json=payload)

        print(stk_response._content)

        if stk_response.status_code == 200:
            # Notify user of payment request
            send_mail(
                'Payment Request Sent',
                f'Dear {customer_name}, we have sent a payment request of KES {total_price} to your phone. Please complete the transaction to confirm your order.',
                'medivana@example.com',  # Replace with your sender email
                [customer_email],
                fail_silently=False,
            )
            messages.success(request, "Payment request sent. Please complete the transaction.")
            return redirect('pharmacy:success')
        else:
            messages.error(request, "Failed to initiate payment. Please try again.")
        
    # return HttpResponse('success')

    return render(request, 'checkout.html', {'cart': cart, 'items': items, 'total_price': total_price})

def mpesa_callback(request):
    if request.method == 'POST':
        callback_data = json.loads(request.body.decode('utf-8'))
        print("Callback Data:", callback_data)
        # Process payment confirmation (e.g., update order status, notify the user)
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Success"})


# def register(request):
    # if request.method == "POST":
    #     username = request.POST['username']
    #     password = request.POST['password']
    #     confirm_password = request.POST['confirm_password']
        
    #     if password != confirm_password:
    #         messages.error(request, "Passwords do not match!")
    #         return redirect('register')
        
    #     if User.objects.filter(username=username).exists():
    #         messages.error(request, "Username already taken!")
    #         return redirect('register')

    #     # Create the user
    #     user = User.objects.create_user(username=username, password=password)
    #     login(request, user)  # Log the user in after registration
    #     return redirect('home')  # Redirect to home page

    # return render(request, 'register.html')
    # if request.method == 'POST':
    #     form = CustomUserCreationForm(request.POST)
    #     if form.is_valid():
    #         form.save()
    #         return redirect('login')
    # else:
    #     form = CustomUserCreationForm()
    # return render(request, 'register.html', {'form': form})

# def login(request):
    # if request.method == 'POST':
    #     form = CustomAuthenticationForm(data=request.POST)
    #     if form.is_valid():
    #         user = form.get_user()
    #         login(request, user)
    #         return redirect('home')
    # else:
    #     form = CustomAuthenticationForm()
    # return render(request, 'login.html', {'form': form})

# def logout(request):
#     logout(request)
#     return redirect('login')
