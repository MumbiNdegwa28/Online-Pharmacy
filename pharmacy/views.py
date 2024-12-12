from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.auth.models import User
from .models import Medicine, Order, Cart, CartItem,Payment
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils.crypto import get_random_string
#mpesa imports
import requests
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


from django.core.mail import send_mail
from django.http import JsonResponse



def home(request):
     medicines = Medicine.objects.all()
     return render(request, 'home.html', {'medicines': medicines})

# def contact(request):
#     return render(request, 'contact.html')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Format email content
        subject = f"New Contact Form Submission from {name}"
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"

        # Send email
        try:
            send_mail(
                subject,
                body,
                'your_email@gmail.com',  # From email
                ['recipient_email@example.com'],  # To email(s)
                fail_silently=False,
            )
            messages.success(request, 'Your message has been sent successfully!')
        except Exception as e:
            print(f"Error sending email: {e}")
            messages.error(request, 'Failed to send your message. Please try again later.')

    return render(request, 'contact.html')



def search_results(request):
    query = request.GET.get('q', '').strip()  # Get the search query
    if query:
        medications = Medicine.objects.filter(name__icontains=query)  # Case-insensitive search by name
    else:
        medications = Medicine.objects.all()  # If no query, return all medicines
    
    return render(request, 'search_results.html', {'query': query, 'medications': medications})

def order_medicine(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)

    # First check if the user is authenticated
    if not request.user.is_authenticated:
        # For anonymous users, ensure a session ID exists or create one
        session_id = request.session.session_key
        if not session_id:
            request.session.create()  # Create session if not present
            session_id = request.session.session_key
    else:
        # For authenticated users, use the user ID
        session_id = None  # No session ID needed for authenticated users

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
                    user=request.user if request.user.is_authenticated else None,
                    session_id=session_id if not request.user.is_authenticated else None,  # Associate with user or session
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
            
            # Handle cart
            # Handle cart using session ID for anonymous users
            if request.user.is_authenticated:
                cart, created = Cart.objects.get_or_create(user=request.user)
            else:
                cart, created = Cart.objects.get_or_create(session_id=session_id)

            # Add or update cart item
            cart_item, _ = CartItem.objects.get_or_create(cart=cart, medicine=medicine)
            if not created:
                cart_item.quantity += quantity
            cart_item.save()

        # Store the order_id in session to keep track of the order
        request.session['order_id'] = order.id
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
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_id = request.session.session_key
        if not session_id:
            request.session.create()  # Ensure a session exists
            session_id = request.session.session_key
         
            return render(request, "cart.html", {"items": [], "total_price": 0})

        cart = Cart.objects.filter(session_id=session_id).first()

    items = CartItem.objects.filter(cart=cart) if cart else []
    total_price = sum(item.total_price() for item in items)
    return render(request, "cart.html", {"items": items, "total_price": total_price})

def update_cart_item(request, item_id):
    """
    Updates the quantity of a cart item or removes it if quantity is set to zero.
    Handles both authenticated users and anonymous sessions.
    """
    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 0))

        # Fetch the cart based on authentication state
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_id = request.session.session_key
            if not session_id:
                messages.error(request, "Session not found. Please try again.")
                return redirect("pharmacy:cart")
            cart = Cart.objects.filter(session_id=session_id).first()

        # Get the specific cart item
        cart_item = get_object_or_404(CartItem, pk=item_id, cart=cart)

        if quantity > 0:
            # Update the quantity if valid
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Cart updated successfully!")
        else:
            # Remove the item if quantity is zero
            cart_item.delete()
            messages.success(request, "Item removed from cart!")

    return redirect("pharmacy:cart")

def remove_cart_item(request, item_id):
    """
    Removes a cart item completely.
    Handles both authenticated users and anonymous sessions.
    """
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_id = request.session.session_key
        if not session_id:
            messages.error(request, "Session not found. Please try again.")
            return redirect("pharmacy:cart")
        cart = Cart.objects.filter(session_id=session_id).first()

    # Get and delete the cart item
    cart_item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    cart_item.delete()
    messages.success(request, "Item removed from cart!")
    return redirect("pharmacy:cart")


def checkout(request, order_id):
    # Retrieve the order object using the order_id from the URL
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('pharmacy:cart')

    # Determine if the user is authenticated or guest
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_id = request.session.session_key
        if not session_id:
            messages.error(request,"Session not found. Please add items to cart")
            return redirect("pharmacy:cart")
        cart = Cart.objects.filter(session_id=session_id).first()

    if not cart:
        messages.error(request,"Your cart is empty. Please add items to proceed")
        return redirect("pharmacy:cart")
    
    # Getting cart items
    items = CartItem.objects.filter(cart=cart)
    total_price = sum(item.quantity * item.medicine.price for item in items)

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        customer_email = request.POST.get('customer_email')
        customer_address = request.POST.get('customer_address')
        phone_number = request.POST.get('phone_number')  # Get phone number from form input

        # If user is a guest, store the details in the session
        if not request.user.is_authenticated:
            request.session['customer_name'] = customer_name
            request.session['customer_email'] = customer_email
            request.session['customer_address'] = customer_address
            request.session['phone_number'] = phone_number
    
        # M-Pesa credentials
        consumer_key = 'qGGvcCbvDKwX1h5S95vPy7gBKaI43xjg9jCzY5iMoGnxZ5G5'
        consumer_secret = '9Q12LudJh8NLnMmgoMGjGPDXgJtniWDrXMj7y6xBuN0dpAQOBRGlV5e6XUJCWrAn'
        #api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        business_shortcode = '174379'  # Replace with your Paybill or Till number
        passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919' 
        callback_url = 'https://communal-thrush-willing.ngrok-free.app/payment/callback'  # Replace with your callback URL

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

        response_data = stk_response.json()

        print(response_data)

        if response_data.get("ResponseCode") == "0":
            # Updating the order record
            order.checkout_request_id = response_data.get("CheckoutRequestID")
            order.status = 'pending_payment'
            order.save()

             # Set session flag for success
            messages.success(request, "Payment request sent. Please complete the transaction.")


            # Notify user of payment request
            send_mail(
                'Payment Request Sent',
                f'Dear {customer_name}, we have sent a payment request of KES {total_price} to your phone. Please complete the transaction to confirm your order.',
                'medivana@example.com',  # Replace with your sender email
                [customer_email],
                fail_silently=False,
            )
            return redirect('pharmacy:success', order_id=order.id)

        else:
            messages.error(request, "Failed to initiate payment. Please try again.")
            return redirect('pharmacy:checkout', order_id=order_id)  # Or wherever you want to redirect in case of failure

    # return HttpResponse('success')

    return render(request, 'checkout.html', {
        'cart': cart,
        'items': items,
        'total_price': total_price,
        })

@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            callback_data = json.loads(request.body.decode('utf-8'))
            print("Callback Data:", json.dumps(callback_data))
            
            # Extract relevant details from the callback data
            result_code = callback_data['Body']['stkCallback']['ResultCode']
            checkout_request_id = callback_data['Body']['stkCallback']['CheckoutRequestID']  # M-Pesa CheckoutRequestID
            result_desc = callback_data['Body']['stkCallback'].get('ResultDesc', '')
            callback_metadata = callback_data['Body']['stkCallback'].get('CallbackMetadata',{}).get('Item',[])

            # Extract transaction_id if available
            transaction_id = None
            for item in callback_metadata:
                if item.get('Name') == 'MpesaReceiptNumber':
                    transaction_id = item.get('Value')
                    break
            
            # Find the corresponding order using the CheckoutRequestID
            order = Order.objects.get(checkout_request_id=checkout_request_id)


            # Step 3: Retrieve cart associated with the order
            if order.user:
                # If the order is tied to a user, fetch the user's cart
                cart = Cart.objects.filter(user=order.user).first()
            else:
                # If the order is not tied to a user (guest user), retrieve the cart using the session
                cart = Cart.objects.filter(session_id=order.session_id).first()

            if not cart:
                raise ValueError("Cart associated with the order not found.")
            
            if result_code == 0:  # Payment successful
                # Clear the cart and update order status
                CartItem.objects.filter(cart=cart).delete()
                order.status = 'Completed'
                order.save()

                # Create payment record
                Payment.objects.create(
                    order=order,
                    amount=order.medicine.price * order.quantity,
                    payment_status="Success",
                    payment_method="M-Pesa",
                    transaction_id=transaction_id,
                    response_code=str(result_code),
                    response_description=result_desc,
                )
                
                return redirect('pharmacy:success', order_id=order.id)  # Redirect to success view after success               

            else:  # Payment failed or canceled
                # Update the order status to "Canceled"
                order.status = 'Cancelled'
                order.save()

                # Create payment record
                Payment.objects.create(
                    order=order,
                    amount=order.medicine.price * order.quantity,
                    payment_status="Failed",
                    payment_method="M-Pesa",
                    transaction_id=transaction_id or "",
                    response_code=str(result_code),
                    response_description=result_desc,
                )

                return redirect('pharmacy:success', order_id=order.id)  # Redirect to success view after failure
            
        except Exception as e:
            print(f"Error processing M-Pesa callback: {str(e)}")
            return JsonResponse({"ResultCode": 1, "ResultDesc": "Failed to process the callback"})
     

def success(request, order_id=None):
    if request.method == "GET" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        
        # Respond to AJAX request for payment status
        # payment_status = request.session.get('payment_status', None)
        # print (f"The payment status at the moment is, {payment_status}")

        # payment_message = request.session.get('payment_message', 'Payment status is not available yet.')
        
        # if payment_status == 'success':
        #     return JsonResponse({
        #         'status': 'Success',
        #         'message': payment_message,
        #     })
        # elif payment_status == 'Failure':
        #     return JsonResponse({
        #         'status': 'Failure',
        #         'message': payment_message,
        #     })
        # else:
        #     return JsonResponse({
        #         'status': 'pending',
        #         'message': 'Payment is still being processed. Please try again later.',
        #     })
    
        # Normal rendering of the success page
        if request.method == "POST":
            # Clear session data when returning to home
            request.session.flush()
            return redirect('pharmacy:home')
    
     # Fetch the order details using the provided `order_id`
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return JsonResponse({
                'status': 'Error',
                'message': "Order not found."
            })
        
        # Determine payment status based on order status
        if order.status == 'Completed':
            payment_status = "Success"
            payment_message = f"Payment Successful. Transaction ID: {order.payment.transaction_id}" if hasattr(order, 'payment') and order.payment else "Payment Successful."
        elif order.status == 'Canceled':
            payment_status = "Failure"
            payment_message = "Payment Failed. Please try again."
        else:
            payment_status = "Pending"
            payment_message = "Payment is still being processed. Please check back later."

        # Return status and message as JSON
        return JsonResponse({
            'status': payment_status,
            'message': payment_message,
        })

    # Normal page rendering (non-AJAX request)
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect("pharmacy:cart")

    # Check if the user is authenticated
    if request.user.is_authenticated:
        user = request.user
        cart = Cart.objects.filter(user=user).first()
    else:
        # Handle guest user (using session_id)
        session_id = request.session.session_key
        if not session_id:
            # If there's no session ID, the cart is empty or there's an issue
            return redirect("pharmacy:cart")
        cart = Cart.objects.filter(session_id=session_id).first()
        user = None  # No user for guest checkout

    # Ensure the cart associated with the order is valid
    # cart = order.cart
    if not cart:
        messages.error(request, "No items found in the cart.")
        return redirect("pharmacy:cart")

    items = CartItem.objects.filter(cart=cart)

    # Prepare a detailed item list with calculated totals
    item_details = [
        {
            "name": item.medicine.name,
            "quantity": item.quantity,
            "price_per_item": item.medicine.price,
            "total_price": item.quantity * item.medicine.price,
        }
        for item in items
    ]

    # Prepare context with total price per item
    total_price = sum(item.quantity * item.medicine.price for item in items)

    # Determine the payment status and message based on the order status
    if order.status == 'Completed':
        payment_status = "success"
        payment_message = f"Payment Successful. Transaction ID: {order.payment.transaction_id}"
    elif order.status == 'Cancelled':
        payment_status = "Failure"
        payment_message = "Payment Failed. Please try again."
    else:
        payment_status = "Pending"
        payment_message = "Payment is still being processed. Please check back later."

    # If the user is authenticated, get their details (name, email)
    if user:
        user_name = user.get_full_name()
        user_email = user.email
    else:
        # For guest users, you can try to fetch data from the session if it was provided
        user_name = order.customer_name or 'Guest'
        user_email = request.customer_email or 'N/A'

    return render(request, 'success.html', {
        "items": item_details,
        "total_price": total_price,
        "user_name": user_name,
        "user_email": user_email,
        "payment_status": payment_status,
        "payment_message": payment_message,
    })


def clear_cart_and_redirect(request):
    # Handle for authenticated users
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart.delete()  # Deletes the user's cart
    else:
        # Handle for guest users
        session_id = request.session.session_key
        if session_id:
            cart = Cart.objects.filter(session_id=session_id).first()
            if cart:
                cart.delete()  # Deletes the guest's cart

    # After clearing the cart, redirect to the home page
    return redirect("pharmacy:home")







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