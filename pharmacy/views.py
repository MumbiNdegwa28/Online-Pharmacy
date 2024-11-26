from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.auth.models import User
from .models import Medicine, Order
from django.contrib import messages

def home(request):
     medicines = Medicine.objects.all()
     return render(request, 'home.html', {'medicines': medicines})

def order_medicine(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)

    if request.method == "POST":
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        customer_address = request.POST.get('customer_address', '').strip()
        quantity = int(request.POST.get('quantity', 0))

        if not customer_name or not customer_phone or not customer_address:
            return render(request, 'order.html', {'medicine': medicine, 'error': 'All fields are required.'})

        if quantity <= 0 or quantity > medicine.stock:
            return render(request, 'order.html', {'medicine': medicine, 'error': 'Invalid quantity or insufficient stock.'})

        # Create the order
        Order.objects.create(
            medicine=medicine,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            quantity=quantity,
        )

        # Update stock
        medicine.stock -= quantity
        medicine.save()

        messages.success(request, "Order placed successfully!")
        return redirect('pharmacy:home')

    return render(request, 'order.html', {'medicine': medicine})

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
