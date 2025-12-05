import razorpay
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.utils.translation import activate, get_language
from .forms import ProfileForm,BranchForm,ServiceForm,UserDetailsForm
# NOTE: Assuming you have Profile, Order, and LaundryShop models
from .models import Profile, Order, LaundryShop ,Service,Branch, Notification
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum
from django.db import IntegrityError
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse # Added for placeholder views
from django.db.models import Count, Q
from datetime import datetime
from django.utils import timezone
from django.views.decorators.http import require_POST
import uuid
from django.http import HttpResponseRedirect

# --- DUMMY DATA (FOR VIEWS) ---

# NOTE: The dashboard template expects a 'cloth_status' list. 
# We'll use the user's last 5 orders as a stand-in.
def get_cloth_status(user):
    # Fetch actual orders and format them
    # For now, return a placeholder list if no orders exist, 
    # or fetch the last few orders
    orders = Order.objects.filter(user=user).order_by('-id')[:5]
    if orders:
        return [{'cloth_name': f"Order #{order.id}", 'status': order.cloth_status, 'delivery_date': order.created_at} for order in orders]
    return [
        {'cloth_name': 'No recent orders', 'status': 'N/A', 'delivery_date': 'N/A'}
    ]

# --- Notification Helper Functions ---

def create_order_notifications(user):
    """Create notifications for user's orders if they don't exist."""
    orders = Order.objects.filter(user=user)

    for order in orders:
        # Check if notification already exists for this order and status
        existing_notification = Notification.objects.filter(
            user=user,
            title__icontains=f'Order #{order.id}',
            message__icontains=order.shop.name
        ).exists()

        if not existing_notification:
            if order.cloth_status == 'Completed':
                Notification.objects.create(
                    user=user,
                    title=f'Order #{order.id} Completed',
                    message=f'Your laundry from {order.shop.name} is ready for pickup',
                    notification_type='completed',
                    icon='fas fa-check-circle',
                    color='#28a745'
                )
            elif order.cloth_status == 'Ready':
                Notification.objects.create(
                    user=user,
                    title=f'Order #{order.id} Ready for Pickup',
                    message=f'Your laundry from {order.shop.name} is ready for pickup',
                    notification_type='ready_pickup',
                    icon='fas fa-box-open',
                    color='#f39c12'
                )
            elif order.cloth_status == 'Washing':
                Notification.objects.create(
                    user=user,
                    title=f'Order #{order.id} In Progress',
                    message=f'Your laundry from {order.shop.name} is being washed',
                    notification_type='status_update',
                    icon='fas fa-tint',
                    color='#17a2b8'
                )

def create_welcome_notifications(user):
    """Create welcome notifications for new users."""
    # Check if welcome notification already exists
    if not Notification.objects.filter(user=user, notification_type='welcome').exists():
        Notification.objects.create(
            user=user,
            title='Welcome to Shine & Bright!',
            message='Thanks for joining our laundry service. Start by exploring nearby shops.',
            notification_type='welcome',
            icon='fas fa-handshake',
            color='#9b59b6'
        )

    # Check if profile reminder exists
    if not Notification.objects.filter(user=user, notification_type='profile_reminder').exists():
        Notification.objects.create(
            user=user,
            title='Complete Your Profile',
            message='Update your profile with your city information to get personalized service recommendations.',
            notification_type='profile_reminder',
            icon='fas fa-user-edit',
            color='#3498db'
        )

# --- Existing Views ---

def index(request):
    return render(request, 'index.html')

def hero(request):
    return render(request, 'home.html')

def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)

            # Send login success email
            login_message = f"""
Hi {user.username},

You have successfully logged in to your Shine & Bright Laundry account.

Login Details:
- Username: {user.username}
- Email: {user.email}
- Login Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

If this login was not initiated by you, please contact our support team immediately and consider changing your password.

For your security, we recommend:
- Using a strong, unique password
- Enabling two-factor authentication if available
- Regularly monitoring your account activity

Thank you for using Shine & Bright!

Best regards,
Shine & Bright Team
🧺✨
"""

            send_mail(
                subject="Login Successful - Shine & Bright",
                message=login_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True,
            )

            messages.success(request, "Login successful!")
            # Redirect to 'next' parameter if present, otherwise check user type
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            # Redirect staff/superusers to admin dashboard, regular users to user dashboard
            elif user.is_staff or user.is_superuser:
                return redirect('admin_dashboard')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password")
            # Preserve the 'next' parameter in the redirect
            next_param = request.GET.get('next', '')
            if next_param:
                return redirect(f"{reverse('login')}?next={next_param}")
            return redirect("login")

    return render(request, "login.html")

def signup(request):
    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password")
        password2 = request.POST.get("password_confirm")

        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        city = request.POST.get("city")
        manual_location = request.POST.get("manual_location", "").strip()

        # Password check
        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("signup")

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long")
            return redirect("signup")

        # Username check
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect("signup")

        # Email check
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("signup")

        # Create user (activate immediately)
        user = User.objects.create_user(username=username, email=email, password=password1, is_active=True)

        # Update Profile with location data (Profile is created automatically via signal)
        try:
            profile = user.profile
            if manual_location:
                # Use manual location input
                profile.city = manual_location
                profile.latitude = None
                profile.longitude = None
            else:
                # Use geolocation data
                profile.latitude = latitude
                profile.longitude = longitude
                profile.city = city
            profile.email_verified = True  # Mark email as verified since no verification needed
            profile.save()
        except Exception as e:
            # Profile creation/update failed, but don't fail signup
            pass

        # Create welcome notifications
        create_welcome_notifications(user)

        # Send welcome email
        welcome_message = f"""
Hi {username},

Welcome to Shine & Bright Laundry Services! 🧺✨

Thank you for registering with us. Your account has been created successfully and is ready to use.

What you can do now:
• Browse and discover nearby laundry shops
• Place orders for washing, dry cleaning, and ironing services
• Track your orders in real-time
• Manage your profile and preferences
• Receive notifications about your orders

Your login credentials:
- Username: {username}
- Email: {email}

You can now log in to your account and start exploring our services.

Thank you for choosing Shine & Bright!

Best regards,
Shine & Bright Team
🧺✨
"""

        send_mail(
            subject="Welcome to Shine & Bright Laundry Services!",
            message=welcome_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=True,
        )

        messages.success(request, "Account created successfully! Welcome email sent to your inbox.")
        return redirect("login")

    return render(request, "signup.html")



@login_required
def profile_page(request):
    return render(request, "profile.html")

def logout_user(request):
    logout(request)
    return redirect("login")

@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            profile = form.save(commit=False)

            profile.latitude = request.POST.get("latitude")
            profile.longitude = request.POST.get("longitude")
            profile.city = request.POST.get("city")

            profile.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
        else:
            messages.error(request, "Invalid data submitted!")

    else:
        form = ProfileForm(instance=profile)

    return render(request, "edit_profile.html", {"form": form, "profile": profile})


@login_required
def user_dashboard(request):
    # Statistics from your original code
    pending = Order.objects.filter(user=request.user, cloth_status="Pending").count()
    completed = Order.objects.filter(user=request.user, cloth_status="Completed").count()

    spent = Order.objects.filter(user=request.user).aggregate(
        total=Sum('amount')
    )["total"] or 0

    # Data needed for the new dashboard template (shops and cloth status table)
    cloth_status = get_cloth_status(request.user)

    # Handle search functionality
    search_query = request.GET.get('search', '')
    services_nearby = []
    shops_nearby = []
    user_city = None

    # Check if user has city data
    try:
        user_profile = request.user.profile
        user_city = user_profile.city if user_profile.city else None
    except:
        user_city = None

    if search_query:
        # Search for services by name and get nearby branches
        services = Service.objects.filter(
            Q(name__icontains=search_query)
        ).select_related('branch__shop').filter(branch__shop__is_approved=True)

        # If user has city, prioritize services from same city
        if user_city:
            city_services = services.filter(branch__shop__city__iexact=user_city)[:10]
            if city_services:
                services_nearby = city_services
            else:
                # If no services in user's city, show all matching services
                services_nearby = services[:10]
        else:
            services_nearby = services[:10]  # Limit to 10 results
    elif user_city:
        # Show services and shops from user's city only if user has city set
        services_nearby = Service.objects.filter(
            branch__shop__is_approved=True,
            branch__shop__city__iexact=user_city
        ).select_related('branch__shop')[:10]

        # Also get shops in user's city
        shops_nearby = LaundryShop.objects.filter(
            is_approved=True,
            city__iexact=user_city
        )[:10]
    # If no search query and no city, services_nearby and shops_nearby remain empty

    # Create notifications for user's orders and welcome messages
    create_order_notifications(request.user)
    create_welcome_notifications(request.user)

    # Get recent notifications from database
    recent_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]

    # Format notifications for template (convert to dict format)
    recent_notifications = [
        {
            'title': notification.title,
            'message': notification.message,
            'time': notification.created_at,
            'icon': notification.icon,
            'color': notification.color,
            'is_read': notification.is_read
        }
        for notification in recent_notifications
    ]

    # Count unread notifications for badge (only if notifications are enabled)
    if hasattr(request.user, 'profile') and request.user.profile.notifications_enabled:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    else:
        unread_count = 0

    return render(request, "user_dashboard.html", {
        "pending_count": pending,
        "completed_count": completed,
        "total_spent": spent,
        "cloth_status": cloth_status, # Added for the 'Your Cloth Status' table
        "services_nearby": services_nearby,
        "shops_nearby": shops_nearby,
        "search_query": search_query,
        "user_city": user_city,
        "recent_notifications": recent_notifications,  # Show up to 5 notifications
        "unread_count": unread_count,
    })

# --- NEW DROPDOWN VIEWS ---

@login_required
def profile_detail(request):
    """Renders the detailed profile page (used by 'View Profile' button in dropdown)."""
    return render(request, 'profile.html') # Reusing the existing 'profile.html' template

@login_required
def settings_view(request):
    """Renders the Settings page and handles notification settings."""
    if request.method == 'POST':
        notifications_enabled = request.POST.get('notifications_enabled') == 'on'
        profile, created = Profile.objects.get_or_create(user=request.user)
        profile.notifications_enabled = notifications_enabled
        profile.save()
        messages.success(request, 'Notification settings updated successfully!')
        return redirect('settings')

    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'setting.html', {'profile': profile})

@login_required
def change_password(request):
    """Handle password change for users."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!

            # Send email notification
            password_change_message = f"""
Hi {user.username},

Your password has been successfully changed on Shine & Bright.

If you did not make this change, please contact our support team immediately.

For security reasons, we recommend:
- Using a strong, unique password
- Enabling two-factor authentication if available
- Regularly monitoring your account activity

Thank you for using our services!

Best regards,
Shine & Bright Team

"""

            send_mail(
                subject=" Password Changed - Shine & Bright",
                message=password_change_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True,
            )

            messages.success(request, 'Your password was successfully updated! A confirmation email has been sent.')
            return redirect('settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {
        'form': form
    })

@login_required
def privacy_policy(request):
    """Display the privacy policy page."""
    return render(request, 'privacy_policy.html')

@login_required
def delete_account(request):
    """Handle account deletion for users."""
    if request.method == 'POST':
        # Get user and related data
        user = request.user
        user_email = user.email
        username = user.username

        # Send confirmation email before deletion
        deletion_message = f"""
Hi {username},

Your Shine & Bright account has been successfully deleted.

We're sorry to see you go! If you change your mind, you can always create a new account.

For your security, we've permanently removed:
- Your account information
- Order history
- Profile data
- All associated personal information

If this deletion was not requested by you, please contact our support team immediately.

Best regards,
Shine & Bright Team
🧺✨
"""

        try:
            send_mail(
                subject="👋 Account Deleted - Shine & Bright",
                message=deletion_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user_email],
                fail_silently=True,
            )
        except:
            # Continue with deletion even if email fails
            pass

        # Delete the user account (this will cascade delete related Profile due to CASCADE)
        user.delete()

        # Log out the user
        logout(request)

        messages.success(request, 'Your account has been successfully deleted. We\'re sorry to see you go!')
        return redirect('home')

    return render(request, 'delete_account.html')

@login_required
def notifications_view(request):
    """Renders the Notifications page."""
    # Ensure notifications are created for the user
    create_order_notifications(request.user)
    create_welcome_notifications(request.user)

    # Mark all notifications as read when user visits the page
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    # Get all notifications for the user
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # Format notifications for template
    notifications = [
        {
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'time': notification.created_at,
            'icon': notification.icon,
            'color': notification.color,
            'is_read': notification.is_read
        }
        for notification in notifications
    ]

    return render(request, 'notifications.html', {
        'notifications': notifications
    })


@login_required
@require_POST
def mark_notifications_read(request):
    """Mark all user's notifications as read."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
def help_view(request):
    """Renders the Help page."""
    return render(request, 'help.html')


@login_required
def my_orders(request):
    """Renders the My Orders page."""
    # Pass user orders data here
    user_orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders.html', {'orders': user_orders})

@login_required
def billing_payments(request):
    """Renders the Billing & Payments page."""
    # Pass billing/payment data here
    user_orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'billing.html', {'orders': user_orders})

@login_required
def shop_detail(request, shop_id):
    """Renders a single laundry shop's detail page."""
    shop = get_object_or_404(LaundryShop, id=shop_id, is_approved=True)

    # Get all branches for this shop
    branches = Branch.objects.filter(shop=shop).prefetch_related('services')

    # If shop has only one branch, redirect to branch detail
    if branches.count() == 1:
        return redirect('branch_detail', branch_id=branches.first().id)

    # Get all services across all branches
    all_services = Service.objects.filter(branch__shop=shop).select_related('branch')

    context = {
        'shop': shop,
        'branches': branches,
        'all_services': all_services,
    }

    return render(request, 'shop_detail.html', context)


@login_required
def branch_detail(request, branch_id):
    """Renders a single branch's detail page."""
    branch = get_object_or_404(Branch, id=branch_id, shop__is_approved=True)

    # Get all services for this branch
    services = Service.objects.filter(branch=branch)

    context = {
        'branch': branch,
        'shop': branch.shop,
        'services': services,
    }

    return render(request, 'branch_detail.html', context)


@login_required
def select_branch_for_order(request, shop_id):
    """Customer selects a branch to place an order from."""
    shop = get_object_or_404(LaundryShop, id=shop_id, is_approved=True)

    branches = Branch.objects.filter(shop=shop).prefetch_related('services')

    context = {
        'shop': shop,
        'branches': branches,
    }

    return render(request, 'select_branch_order.html', context)


@login_required
def select_services(request, shop_id, branch_id=None):
    """Renders the service selection page for a shop/branch."""
    shop = get_object_or_404(LaundryShop, id=shop_id, is_approved=True)

    if branch_id:
        # Services for specific branch
        branch = get_object_or_404(Branch, id=branch_id, shop=shop)
        services = Service.objects.filter(branch=branch)
        context = {
            'shop': shop,
            'branch': branch,
            'services': services,
        }
    else:
        # Get all services for this shop across all branches (legacy support)
        services = Service.objects.filter(branch__shop=shop).select_related('branch')
        context = {
            'shop': shop,
            'services': services,
        }

    return render(request, 'select_services.html', context)


@login_required
def create_order(request, shop_id):
    """Create order and initiate Razorpay payment."""
    if request.method != 'POST':
        return redirect('select_services', shop_id=shop_id)

    shop = get_object_or_404(LaundryShop, id=shop_id, is_approved=True)
    selected_services = request.POST.getlist('selected_services')

    if not selected_services:
        messages.error(request, 'Please select at least one service.')
        return redirect('select_services', shop_id=shop_id)

    # Calculate total amount
    total_amount = 0
    order_items = []
    branch = None

    for service_id in selected_services:
        try:
            service = Service.objects.get(id=service_id, branch__shop=shop)
            quantity = int(request.POST.get(f'quantity_{service_id}', 1))
            if quantity < 1:
                quantity = 1

            # Ensure all services are from the same branch
            if branch is None:
                branch = service.branch
            elif branch != service.branch:
                messages.error(request, 'All selected services must be from the same branch.')
                return redirect('select_services', shop_id=shop_id)

            if service.price:
                item_total = service.price * quantity
                total_amount += item_total
                order_items.append({
                    'service': service,
                    'quantity': quantity,
                    'price': service.price,
                    'total': item_total
                })
        except (Service.DoesNotExist, ValueError):
            continue

    if total_amount == 0:
        messages.error(request, 'Unable to calculate order total. Please try again.')
        return redirect('select_services', shop_id=shop_id)

    if branch is None:
        messages.error(request, 'Unable to determine branch for order. Please try again.')
        return redirect('select_services', shop_id=shop_id)

    # Create order in database
    order = Order.objects.create(
        user=request.user,
        shop=shop,
        branch=branch,
        amount=total_amount,
        cloth_status='Pending'
    )

    # Store order items in session for later use
    request.session['order_items'] = [
        {
            'service_id': item['service'].id,
            'service_name': item['service'].name,
            'quantity': item['quantity'],
            'price': float(item['price']),
            'total': float(item['total'])
        } for item in order_items
    ]
    request.session['order_id'] = order.id
    request.session['shop_id'] = shop.id

    # TEMPORARILY SKIP RAZORPAY - Store order details in session for later
    request.session['total_amount'] = float(total_amount)
    # We'll create Razorpay order later in the payment view

    # Send order notification emails to admin and shop
    try:
        # Get admin email (first superuser or staff user)
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()
        admin_email = admin_user.email if admin_user else settings.EMAIL_HOST_USER

        # Prepare order details
        order_items_text = "\n".join([
            f"- {item['service_name']} (x{item['quantity']}) - ₹{item['total']}"
            for item in request.session.get('order_items', [])
        ])

        # Email to Admin
        admin_subject = f"New Order Placed - Order #{order.id}"
        admin_message = f"""
Dear Admin,

A new order has been placed on Shine & Bright Laundry System.

Order Details:
- Order ID: #{order.id}
- Customer: {request.user.username} ({request.user.email})
- Shop: {shop.name}
- Branch: {branch.name if branch else 'Main Branch'}
- Total Amount: ₹{total_amount}

Order Items:
{order_items_text}

Delivery Details:
- Name: {order.delivery_name or 'Not provided yet'}
- Address: {order.delivery_address or 'Not provided yet'}
- Phone: {order.delivery_phone or 'Not provided yet'}

Please process this order promptly.

Best regards,
Shine & Bright System
🧺✨
"""

        # Email to Shop Owner
        shop_subject = f"New Order Received - Order #{order.id}"
        shop_message = f"""
Dear {shop.name} Team,

You have received a new order on Shine & Bright Laundry System.

Order Details:
- Order ID: #{order.id}
- Customer: {request.user.username}
- Customer Email: {request.user.email}
- Branch: {branch.name if branch else 'Main Branch'}
- Total Amount: ₹{total_amount}

Order Items:
{order_items_text}

Please prepare to process this order. The customer will provide delivery details shortly.

You can manage this order through your shop dashboard.

Best regards,
Shine & Bright System
🧺✨
"""

        # Send emails
        send_mail(
            subject=admin_subject,
            message=admin_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[admin_email],
            fail_silently=True,
        )

        send_mail(
            subject=shop_subject,
            message=shop_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[shop.email],
            fail_silently=True,
        )

    except Exception as e:
        # Log the error but don't fail the order process
        print(f"Failed to send order notification emails: {e}")

    # Redirect to user details page
    return redirect('user_details')


@login_required
def payment(request):
    """Render payment page for the order."""
    order_id = request.session.get('order_id')
    if not order_id:
        messages.error(request, 'No order found. Please start over.')
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Get order items from session
    order_items = request.session.get('order_items', [])
    total_amount = request.session.get('total_amount', order.amount)

    # Create Razorpay order here instead of in create_order
    total_amount = request.session.get('total_amount', 0)

    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            'amount': int(total_amount * 100),  # Amount in paisa
            'currency': 'INR',
            'payment_capture': '1'  # Auto capture
        })
        razorpay_order_id = razorpay_order['id']
        request.session['razorpay_order_id'] = razorpay_order_id
    except razorpay.errors.BadRequestError:
        messages.error(request, 'Payment service is currently unavailable. Please contact support.')
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, 'Unable to process payment at this time. Please try again later.')
        return redirect('dashboard')

    context = {
        'order': order,
        'order_items': order_items,
        'total_amount': total_amount,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'shop': order.shop,
    }

    return render(request, 'payment.html', context)


@login_required
def user_details(request):
    """Collect user delivery details before payment."""
    order_id = request.session.get('order_id')
    if not order_id:
        messages.error(request, 'No order found. Please start over.')
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        form = UserDetailsForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, 'Delivery details saved successfully.')
            return redirect('payment')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserDetailsForm(instance=order)

    context = {
        'form': form,
        'order': order,
    }

    return render(request, 'user_details.html', context)


@login_required
def payment_success(request):
    """Handle successful payment."""
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_signature = request.POST.get('razorpay_signature')

    # Check if Razorpay keys are configured
    if not settings.RAZORPAY_KEY_ID or settings.RAZORPAY_KEY_ID == 'your-razorpay-key-id':
        messages.error(request, 'Payment service is not configured. Please contact support.')
        return redirect('dashboard')

    # Verify payment signature
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
    except razorpay.errors.BadRequestError:
        messages.error(request, 'Payment verification failed due to service configuration. Please contact support.')
        return redirect('dashboard')
    except razorpay.errors.SignatureVerificationError:
        messages.error(request, 'Payment verification failed. Please contact support.')
        return redirect('dashboard')

        # Payment verified, update order status
        order_id = request.session.get('order_id')
        if order_id:
            order = get_object_or_404(Order, id=order_id, user=request.user)
            order.cloth_status = 'Washing'  # Move to next status
            order.save()

            # Send payment success email
            payment_success_message = f"""
Hi {order.user.get_full_name() or order.user.username},

Your payment has been successfully processed!

Order Details:
- Order ID: #{order.id}
- Amount Paid: ₹{order.amount}
- Shop: {order.shop.name}
- Status: {order.get_cloth_status_display()}

Delivery Information:
- Name: {order.delivery_name or 'Not provided'}
- Address: {order.delivery_address or 'Not provided'}
- Phone: {order.delivery_phone or 'Not provided'}

Your laundry will be processed shortly. You can track your order status in your dashboard.

Thank you for choosing Shine & Bright!

Best regards,
Shine & Bright Team
🧺✨
"""

            try:
                send_mail(
                    subject=f"Payment Successful - Order #{order.id}",
                    message=payment_success_message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[order.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                # Log the error but don't fail the payment
                print(f"Failed to send payment success email: {e}")

            # Clear session
            request.session.pop('order_items', None)
            request.session.pop('order_id', None)
            request.session.pop('shop_id', None)
            request.session.pop('razorpay_order_id', None)

            messages.success(request, f'Payment successful! Your order #{order.id} has been placed.')
            return redirect('orders')

    except razorpay.errors.SignatureVerificationError:
        messages.error(request, 'Payment verification failed. Please contact support.')
        return redirect('dashboard')

    messages.error(request, 'Payment failed. Please try again.')
    return redirect('dashboard')


@login_required
def payment_failed(request):
    """Handle failed payment."""
    order_id = request.session.get('order_id')
    if order_id:
        # Delete the order since payment failed
        Order.objects.filter(id=order_id, user=request.user).delete()

    # Clear session
    request.session.pop('order_items', None)
    request.session.pop('order_id', None)
    request.session.pop('shop_id', None)
    request.session.pop('razorpay_order_id', None)

    messages.error(request, 'Payment failed. Please try again.')
    return redirect('dashboard')


# --- ADMIN DASHBOARD VIEWS ---

def is_staff_user(user):
    """Check if user is staff or superuser."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_dashboard(request):
    """Admin dashboard with statistics and management tools."""
    
    # Statistics
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(cloth_status="Pending").count()
    completed_orders = Order.objects.filter(cloth_status="Completed").count()
    washing_orders = Order.objects.filter(cloth_status="Washing").count()
    ready_orders = Order.objects.filter(cloth_status="Ready").count()
    
    # Revenue
    total_revenue = Order.objects.aggregate(total=Sum('amount'))['total'] or 0
    today_revenue = Order.objects.filter(
        created_at__date=datetime.now().date()
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Users
    total_users = User.objects.count()
    new_users_today = User.objects.filter(
        date_joined__date=datetime.now().date()
    ).count()
    
    # Shops
    total_shops = LaundryShop.objects.count()
    open_shops = LaundryShop.objects.filter(is_open=True).count()
    pending_approvals = LaundryShop.objects.filter(is_approved=False).count()
    
    # Recent orders (last 10)
    recent_orders = Order.objects.select_related('user', 'shop').order_by('-created_at')[:10]
    
    # Orders by status
    orders_by_status = Order.objects.values('cloth_status').annotate(count=Count('id')).order_by('cloth_status')
    
    # Recent users (last 5)
    recent_users = User.objects.order_by('-date_joined')[:5]

    # Branches
    total_branches = Branch.objects.count()
    recent_branches = Branch.objects.select_related('shop').order_by('-created_at')[:10]

    # Shops with their branches
    shops_with_branches = LaundryShop.objects.prefetch_related('branches').all()

    context = {
        # Statistics
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'washing_orders': washing_orders,
        'ready_orders': ready_orders,
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'total_users': total_users,
        'new_users_today': new_users_today,
        'total_shops': total_shops,
        'open_shops': open_shops,
        'pending_approvals': pending_approvals,
        'total_branches': total_branches,

        # Data
        'recent_orders': recent_orders,
        'orders_by_status': orders_by_status,
        'recent_users': recent_users,
        'recent_branches': recent_branches,
        'all_shops': LaundryShop.objects.all(),
        'shops_with_branches': shops_with_branches,
    }
    
    return render(request, 'admin_dashboard.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_update_order_status(request, order_id):
    """Update order status (AJAX endpoint)."""
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.cloth_status
            order.cloth_status = new_status
            order.save()

            # Send status update notification emails
            try:
                # Email to Customer
                customer_subject = f"Order Status Updated - Order #{order.id}"
                customer_message = f"""
Hi {order.user.get_full_name() or order.user.username},

Your order status has been updated!

Order Details:
- Order ID: #{order.id}
- Shop: {order.shop.name}
- Previous Status: {old_status}
- New Status: {new_status}
- Amount: ₹{order.amount}

Delivery Information:
- Name: {order.delivery_name or 'Not provided'}
- Address: {order.delivery_address or 'Not provided'}
- Phone: {order.delivery_phone or 'Not provided'}

{'Your laundry is ready for pickup!' if new_status == 'Ready' else ''}
{'Your order has been completed and delivered. Thank you for choosing us!' if new_status == 'Completed' else ''}

You can track your order status in your dashboard.

Best regards,
Shine & Bright Team
🧺✨
"""

                # Email to Shop (if status updated by admin)
                if request.user.is_staff or request.user.is_superuser:
                    shop_subject = f"Order Status Updated by Admin - Order #{order.id}"
                    shop_message = f"""
Dear {order.shop.name} Team,

Order #{order.id} status has been updated by an administrator.

Order Details:
- Order ID: #{order.id}
- Customer: {order.user.username}
- Previous Status: {old_status}
- New Status: {new_status}
- Amount: ₹{order.amount}

Please take appropriate action based on the new status.

Best regards,
Shine & Bright System
🧺✨
"""

                    send_mail(
                        subject=shop_subject,
                        message=shop_message,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[order.shop.email],
                        fail_silently=True,
                    )

                # Send email to customer
                send_mail(
                    subject=customer_subject,
                    message=customer_message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[order.user.email],
                    fail_silently=True,
                )

            except Exception as e:
                print(f"Failed to send status update emails: {e}")

            return JsonResponse({'success': True, 'message': 'Order status updated successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_orders(request):
    """View all orders with filtering."""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    orders = Order.objects.select_related('user', 'shop').order_by('-created_at')
    
    if status_filter:
        orders = orders.filter(cloth_status=status_filter)
    
    if search_query:
        orders = orders.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'current_status': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'admin_orders.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_users(request):
    """View all users."""
    search_query = request.GET.get('search', '')
    
    users = User.objects.all().order_by('-date_joined')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    context = {
        'users': users,
        'search_query': search_query,
    }
    
    return render(request, 'admin_users.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_shops(request):
    """View and manage shops."""
    shops = LaundryShop.objects.all().order_by('name')

    context = {
        'shops': shops,
    }

    return render(request, 'admin_shops.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_approve_shop(request, shop_id):
    """Approve a shop."""
    if request.method == 'POST':
        shop = get_object_or_404(LaundryShop, id=shop_id)
        shop.is_approved = True
        shop.save()
        return JsonResponse({'success': True, 'message': 'Shop approved successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_reject_shop(request, shop_id):
    """Reject a shop."""
    if request.method == 'POST':
        shop = get_object_or_404(LaundryShop, id=shop_id)
        shop.delete()  # Or set is_approved=False and is_open=False
        return JsonResponse({'success': True, 'message': 'Shop rejected and removed'})
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


# --- SHOP AUTHENTICATION VIEWS ---

def shop_register(request):
    """Shop registration page."""
    if request.method == "POST":
        shop_name = request.POST.get("shop_name")
        email = request.POST.get("email")
        password1 = request.POST.get("password")
        password2 = request.POST.get("password_confirm")
        address = request.POST.get("address", "")
        phone = request.POST.get("phone", "")
        latitude = request.POST.get("latitude", "")
        longitude = request.POST.get("longitude", "")
        city = request.POST.get("city", "")

        # Validation
        if not shop_name or not email or not password1 or not password2:
            messages.error(request, "All fields are required")
            return redirect("shop_register")

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("shop_register")

        if len(password1) < 6:
            messages.error(request, "Password must be at least 6 characters long")
            return redirect("shop_register")

        if LaundryShop.objects.filter(name=shop_name).exists():
            messages.error(request, "Shop name already taken")
            return redirect("shop_register")

        if LaundryShop.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("shop_register")

        # Create shop
        shop = LaundryShop(
            name=shop_name,
            email=email,
            address=address,
            phone=phone,
            city=city,
            latitude=latitude,
            longitude=longitude,
            is_approved=False
        )
        shop.set_password(password1)
        shop.save()

        messages.success(request, "Shop registered successfully! Please login.")
        return redirect("shop_login")

    return render(request, "shop_register.html")


def shop_login(request):
    """Shop login page."""
    if request.method == "POST":
        shop_name = request.POST.get("shop_name")
        password = request.POST.get("password")

        if not shop_name or not password:
            messages.error(request, "Please enter both shop name and password")
            return redirect("shop_login")

        try:
            shop = LaundryShop.objects.get(name=shop_name)
            if shop.check_password(password):
                if not shop.is_approved:
                    messages.error(request, "Your shop is pending approval. Please wait for admin approval.")
                    return redirect("shop_login")
                # Store shop ID in session
                request.session['shop_id'] = shop.id
                request.session['shop_name'] = shop.name

                # Send login success email
                login_message = f"""
Hi {shop.name},

You have successfully logged in to your Shine & Bright Laundry shop account.

Login Details:
- Shop Name: {shop.name}
- Email: {shop.email}
- Login Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

If this login was not initiated by you, please contact our support team immediately and consider changing your password.

For your security, we recommend:
- Using a strong, unique password
- Regularly monitoring your account activity
- Keeping your shop information up to date

Thank you for using Shine & Bright!

Best regards,
Shine & Bright Team
🧺✨
"""

                send_mail(
                    subject="Shop Login Successful - Shine & Bright",
                    message=login_message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[shop.email],
                    fail_silently=True,
                )

                messages.success(request, f"Welcome back, {shop.name}!")
                return redirect("shop_dashboard")
            else:
                messages.error(request, "Invalid shop name or password")
        except LaundryShop.DoesNotExist:
            messages.error(request, "Invalid shop name or password")

        return redirect("shop_login")

    return render(request, "shop_login.html")


def shop_logout(request):
    """Shop logout."""
    if 'shop_id' in request.session:
        shop_name = request.session.get('shop_name', 'Shop')
        del request.session['shop_id']
        del request.session['shop_name']
        messages.success(request, f"Logged out successfully from {shop_name}")
    return redirect("shop_login")


def is_shop_logged_in(request):
    """Check if shop is logged in."""
    return 'shop_id' in request.session


def shop_login_required(view_func):
    """Decorator to require shop login."""
    from functools import wraps
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_shop_logged_in(request):
            messages.error(request, "Please login to access this page")
            return redirect("shop_login")
        return view_func(request, *args, **kwargs)
    return wrapper


@shop_login_required
def shop_notifications(request):
    """Shop notifications page."""
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)

    # Generate comprehensive shop notifications
    notifications = []

    # Get all shop orders for notifications
    shop_orders = Order.objects.filter(shop=shop).select_related('user', 'branch').order_by('-created_at')

    for order in shop_orders:
        # Order placed notification
        notifications.append({
            'type': 'order_placed',
            'title': f'New Order #{order.id} Placed',
            'message': f'Order from {order.user.username} at {order.branch.name if order.branch else "Main Branch"} - ₹{order.amount}',
            'time': order.created_at,
            'icon': 'fas fa-shopping-cart',
            'color': '#28a745'
        })

        # Status-based notifications
        if order.cloth_status == 'Washing':
            notifications.append({
                'type': 'status_update',
                'title': f'Order #{order.id} - Washing Started',
                'message': f'Laundry for {order.user.username} is now being washed',
                'time': order.created_at,
                'icon': 'fas fa-tint',
                'color': '#17a2b8'
            })
        elif order.cloth_status == 'Drying':
            notifications.append({
                'type': 'status_update',
                'title': f'Order #{order.id} - Drying Started',
                'message': f'Laundry for {order.user.username} is now being dried',
                'time': order.created_at,
                'icon': 'fas fa-wind',
                'color': '#f39c12'
            })
        elif order.cloth_status == 'Ironing':
            notifications.append({
                'type': 'status_update',
                'title': f'Order #{order.id} - Ironing Started',
                'message': f'Laundry for {order.user.username} is now being ironed',
                'time': order.created_at,
                'icon': 'fas fa-fire',
                'color': '#e74c3c'
            })
        elif order.cloth_status == 'Ready':
            notifications.append({
                'type': 'ready_pickup',
                'title': f'Order #{order.id} Ready for Pickup',
                'message': f'Laundry for {order.user.username} is ready! Please notify customer.',
                'time': order.created_at,
                'icon': 'fas fa-box-open',
                'color': '#f39c12'
            })
        elif order.cloth_status == 'Completed':
            notifications.append({
                'type': 'completed',
                'title': f'Order #{order.id} Completed',
                'message': f'Order for {order.user.username} has been successfully completed and delivered.',
                'time': order.created_at,
                'icon': 'fas fa-check-circle',
                'color': '#28a745'
            })

    # Add some general notifications if shop has no orders
    if not notifications:
        notifications = [
            {
                'type': 'welcome',
                'title': f'Welcome to {shop.name} Dashboard',
                'message': 'Manage your orders and track your business performance',
                'time': shop.created_at,
                'icon': 'fas fa-store',
                'color': '#3498db'
            },
            {
                'type': 'add_branches',
                'title': 'Add Branches',
                'message': 'Expand your reach by adding multiple branches to serve more customers',
                'time': shop.created_at,
                'icon': 'fas fa-map-marker-alt',
                'color': '#9b59b6'
            },
            {
                'type': 'add_services',
                'title': 'Add Services',
                'message': 'Expand your offerings by adding more laundry services to attract more customers',
                'time': shop.created_at,
                'icon': 'fas fa-concierge-bell',
                'color': '#e67e22'
            }
        ]

    # Sort notifications by time (most recent first)
    notifications.sort(key=lambda x: x['time'], reverse=True)

    return render(request, 'shop_notifications.html', {
        'shop': shop,
        'notifications': notifications
    })


@shop_login_required
def shop_dashboard(request):
    """Main shop dashboard with branch overview."""
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)

    # Get all branches for this shop
    branches = Branch.objects.filter(shop=shop).prefetch_related('services')

    # Get overall shop statistics
    shop_orders = Order.objects.filter(shop=shop)
    total_orders = shop_orders.count()
    pending_orders = shop_orders.filter(cloth_status="Pending").count()
    completed_orders = shop_orders.filter(cloth_status="Completed").count()
    total_revenue = shop_orders.aggregate(total=Sum('amount'))['total'] or 0

    # Today's revenue
    today_revenue = shop_orders.filter(
        created_at__date=datetime.now().date()
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Recent orders across all branches
    recent_orders = Order.objects.filter(shop=shop).select_related('user', 'branch').order_by('-created_at')[:10]

    # Branch statistics
    branch_stats = []
    for branch in branches:
        branch_orders = Order.objects.filter(branch=branch)
        branch_stats.append({
            'branch': branch,
            'total_orders': branch_orders.count(),
            'pending_orders': branch_orders.filter(cloth_status="Pending").count(),
            'completed_orders': branch_orders.filter(cloth_status="Completed").count(),
            'revenue': branch_orders.aggregate(total=Sum('amount'))['total'] or 0,
        })

    # Generate shop notifications
    shop_notifications = []

    # Recent orders notifications
    recent_orders_for_notifications = Order.objects.filter(shop=shop).order_by('-created_at')[:10]

    for order in recent_orders_for_notifications:
        if order.cloth_status == 'Pending':
            shop_notifications.append({
                'title': f'New Order #{order.id}',
                'message': f'Order from {order.user.username} - ₹{order.amount}',
                'time': order.created_at,
                'icon': 'fas fa-shopping-cart',
                'color': '#28a745'
            })
        elif order.cloth_status == 'Ready':
            shop_notifications.append({
                'title': f'Order #{order.id} Ready',
                'message': f'Order from {order.user.username} is ready for pickup',
                'time': order.created_at,
                'icon': 'fas fa-box-open',
                'color': '#f39c12'
            })

    # Add some general notifications if no recent activity
    if not shop_notifications:
        shop_notifications = [
            {
                'title': 'Welcome to Shop Dashboard',
                'message': 'Manage your orders and track your business performance',
                'time': timezone.now(),
                'icon': 'fas fa-store',
                'color': '#3498db'
            },
            {
                'title': 'Add Services',
                'message': 'Expand your offerings by adding more laundry services',
                'time': timezone.now(),
                'icon': 'fas fa-concierge-bell',
                'color': '#9b59b6'
            }
        ]

    # Sort notifications by time (most recent first)
    shop_notifications.sort(key=lambda x: x['time'], reverse=True)

    context = {
        'shop': shop,
        'branches': branches,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'recent_orders': recent_orders,
        'branch_stats': branch_stats,
        'shop_notifications': shop_notifications[:5],  # Show up to 5 notifications
    }

    return render(request, 'shop_dashboard.html', context)


@shop_login_required
def select_branch(request):
    """Page to select a branch for viewing orders."""
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)

    branches = Branch.objects.filter(shop=shop).prefetch_related('services')

    context = {
        'shop': shop,
        'branches': branches,
    }

    return render(request, 'select_branch.html', context)


@shop_login_required
def branch_orders(request, branch_id):
    """View orders for a specific branch."""
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)
    branch = get_object_or_404(Branch, id=branch_id, shop=shop)

    # Get orders for this branch
    branch_orders = Order.objects.filter(branch=branch).order_by('-created_at')

    # Statistics for this branch
    total_orders = branch_orders.count()
    pending_orders = branch_orders.filter(cloth_status="Pending").count()
    washing_orders = branch_orders.filter(cloth_status="Washing").count()
    drying_orders = branch_orders.filter(cloth_status="Drying").count()
    ironing_orders = branch_orders.filter(cloth_status="Ironing").count()
    ready_orders = branch_orders.filter(cloth_status="Ready").count()
    completed_orders = branch_orders.filter(cloth_status="Completed").count()
    total_revenue = branch_orders.aggregate(total=Sum('amount'))['total'] or 0

    # Today's revenue for this branch
    today_revenue = branch_orders.filter(
        created_at__date=datetime.now().date()
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Recent orders for this branch
    recent_orders = branch_orders.select_related('user')[:20]  # Show more orders on branch page

    context = {
        'shop': shop,
        'branch': branch,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'washing_orders': washing_orders,
        'drying_orders': drying_orders,
        'ironing_orders': ironing_orders,
        'ready_orders': ready_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'recent_orders': recent_orders,
    }

    return render(request, 'branch_orders.html', context)


@shop_login_required
def shop_update_order_status(request, order_id):
    """Update order status for shop (AJAX endpoint)."""
    if request.method == 'POST':
        shop_id = request.session.get('shop_id')
        shop = get_object_or_404(LaundryShop, id=shop_id)
        order = get_object_or_404(Order, id=order_id)

        # Verify that the order belongs to this shop
        if order.shop != shop:
            return JsonResponse({'success': False, 'message': 'You do not have permission to update this order'}, status=403)

        new_status = request.POST.get('status')

        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.cloth_status
            order.cloth_status = new_status
            order.save()

            # Send status update notification emails
            try:
                # Email to Customer
                customer_subject = f"Order Status Updated - Order #{order.id}"
                customer_message = f"""
Hi {order.user.get_full_name() or order.user.username},

Your order status has been updated by {order.shop.name}!

Order Details:
- Order ID: #{order.id}
- Shop: {order.shop.name}
- Branch: {order.branch.name if order.branch else 'Main Branch'}
- Previous Status: {old_status}
- New Status: {new_status}
- Amount: ₹{order.amount}

Delivery Information:
- Name: {order.delivery_name or 'Not provided'}
- Address: {order.delivery_address or 'Not provided'}
- Phone: {order.delivery_phone or 'Not provided'}

{'Your laundry is ready for pickup!' if new_status == 'Ready' else ''}
{'Your order has been completed and delivered. Thank you for choosing us!' if new_status == 'Completed' else ''}

You can track your order status in your dashboard.

Best regards,
{order.shop.name} Team
🧺✨
"""

                # Email to Admin (when shop updates status)
                admin_user = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()
                if admin_user:
                    admin_subject = f"Order Status Updated by Shop - Order #{order.id}"
                    admin_message = f"""
Dear Admin,

Order #{order.id} status has been updated by {order.shop.name}.

Order Details:
- Order ID: #{order.id}
- Customer: {order.user.username} ({order.user.email})
- Shop: {order.shop.name}
- Branch: {order.branch.name if order.branch else 'Main Branch'}
- Previous Status: {old_status}
- New Status: {new_status}
- Amount: ₹{order.amount}

The shop has updated the order status. Please review if necessary.

Best regards,
Shine & Bright System
🧺✨
"""

                    send_mail(
                        subject=admin_subject,
                        message=admin_message,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[admin_user.email],
                        fail_silently=True,
                    )

                # Send email to customer
                send_mail(
                    subject=customer_subject,
                    message=customer_message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[order.user.email],
                    fail_silently=True,
                )

            except Exception as e:
                print(f"Failed to send status update emails: {e}")

            return JsonResponse({'success': True, 'message': 'Order status updated successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)



# ---------- Branch Views ----------
@shop_login_required
def add_branch(request):
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)

    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.shop = shop
            branch.save()
            messages.success(request, 'Branch created successfully.')
            return redirect('shop_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BranchForm()

    return render(request, 'add_branch.html', {'form': form, 'shop': shop})


@shop_login_required
def edit_branch(request, branch_id):
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)
    branch = get_object_or_404(Branch, id=branch_id, shop=shop)

    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Branch updated.')
            return redirect('shop_dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = BranchForm(instance=branch)

    return render(request, 'edit_branch.html', {'form': form, 'shop': shop, 'branch': branch})


@shop_login_required
@require_POST
def delete_branch(request, branch_id):
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)
    branch = get_object_or_404(Branch, id=branch_id, shop=shop)
    branch.delete()
    messages.success(request, 'Branch deleted.')
    return redirect('shop_dashboard')


# ---------- Service Views ----------
@shop_login_required
def add_service(request, branch_id):
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)
    branch = get_object_or_404(Branch, id=branch_id, shop=shop)

    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.branch = branch
            try:
                service.save()
                messages.success(request, 'Service added successfully.')
                return redirect('shop_dashboard')
            except IntegrityError:
                messages.error(request, 'This service already exists for this branch.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ServiceForm()

    return render(request, 'add_service.html', {'form': form, 'shop': shop, 'branch': branch})


@shop_login_required
def edit_service(request, service_id):
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)
    service = get_object_or_404(Service, id=service_id, branch__shop=shop)

    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service updated successfully.')
            return redirect('branch_orders', branch_id=service.branch.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ServiceForm(instance=service)

    return render(request, 'edit_service.html', {
        'form': form,
        'shop': shop,
        'service': service,
        'branch': service.branch
    })


@shop_login_required
@require_POST
def delete_service(request, service_id):
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)
    service = get_object_or_404(Service, id=service_id, branch__shop=shop)
    branch_id = service.branch.id
    service.delete()
    messages.success(request, 'Service deleted.')
    return redirect('branch_orders', branch_id=branch_id)

