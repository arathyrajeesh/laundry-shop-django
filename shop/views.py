import razorpay
from django.shortcuts import render, redirect, get_object_or_404
from .payment_utils import (
    create_razorpay_order,
    capture_payment_and_transfer,
    verify_payment_signature,
    calculate_commission,
    get_razorpay_client,
)
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import CustomPasswordChangeForm
from django.utils.translation import activate, get_language
from .forms import ProfileForm,BranchForm,ServiceForm,UserDetailsForm,LaundryShopForm,ShopBankDetailsForm
# NOTE: Assuming you have Profile, Order, and LaundryShop models
from .models import Profile, Order, LaundryShop ,Service,Branch, Notification, ShopRating, ServiceRating, BranchRating, Cloth, OrderItem
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum, Avg
from django.db import IntegrityError
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse # Added for placeholder views
from django.db.models import Count, Q
from datetime import datetime
from django.views.decorators.http import require_POST
import uuid
from django.http import HttpResponseRedirect
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
import uuid
from django.core.mail import send_mail
from django.conf import settings
from .models import LaundryShop, ShopPasswordResetToken,NewsletterSubscriber
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Order, Profile
from django.db.models import Count

def splash(request):
    return render(request, 'splash.html')
def generate_payment_receipt_pdf(order, order_items):
    """Generate a PDF payment receipt for the order."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=30,
        alignment=1,  # Center alignment
    )

    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
    )

    normal_style = styles['Normal']

    story = []

    # Title
    story.append(Paragraph("Shine & Bright Laundry Services", title_style))
    story.append(Paragraph("Payment Receipt", heading_style))
    story.append(Spacer(1, 12))

    # Order details
    story.append(Paragraph(f"<b>Order ID:</b> #{order.id}", normal_style))
    story.append(Paragraph(f"<b>Customer:</b> {order.user.get_full_name() or order.user.username}", normal_style))
    story.append(Paragraph(f"<b>Email:</b> {order.user.email}", normal_style))
    story.append(Paragraph(f"<b>Shop:</b> {order.shop.name}", normal_style))
    if order.branch:
        story.append(Paragraph(f"<b>Branch:</b> {order.branch.name}", normal_style))
    story.append(Paragraph(f"<b>Order Date:</b> {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Paragraph(f"<b>Payment Date:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 12))

    # Delivery details
    if order.delivery_name or order.delivery_address or order.delivery_phone:
        story.append(Paragraph("<b>Delivery Details:</b>", heading_style))
        if order.delivery_name:
            story.append(Paragraph(f"Name: {order.delivery_name}", normal_style))
        if order.delivery_address:
            story.append(Paragraph(f"Address: {order.delivery_address}", normal_style))
        if order.delivery_phone:
            story.append(Paragraph(f"Phone: {order.delivery_phone}", normal_style))
        if order.special_instructions:
            story.append(Paragraph(f"Instructions: {order.special_instructions}", normal_style))
        story.append(Spacer(1, 12))

    # Order items table
    story.append(Paragraph("<b>Order Items:</b>", heading_style))

    # Table data
    table_data = [['Service', 'Cloth', 'Quantity', 'Price', 'Total']]
    for item in order_items:
        service_name = item.get('service_name', 'Service')
        cloth_name = item.get('cloth_name', '')
        quantity = item.get('quantity', 1)
        price = item.get('price', 0)
        total = item.get('total', 0)
        table_data.append([
            service_name,
            cloth_name,
            str(quantity),
            f"₹{price:.2f}",
            f"₹{total:.2f}"
        ])

    # Add total row
    table_data.append(['', '', '<b>Total</b>', f"<b>₹{order.amount:.2f}</b>"])

    # Create table
    table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
    ]))

    story.append(table)
    story.append(Spacer(1, 20))

    # Payment status
    story.append(Paragraph("<b>Payment Status: Completed</b>", ParagraphStyle(
        'PaymentStatus',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.green,
        alignment=1,
    )))
    story.append(Spacer(1, 20))

    # Footer
    story.append(Paragraph("Thank you for choosing Shine & Bright Laundry Services!", ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        spaceBefore=20,
    )))
    story.append(Paragraph("🧺✨", ParagraphStyle(
        'Emoji',
        parent=styles['Normal'],
        fontSize=14,
        alignment=1,
    )))

    doc.build(story)
    buffer.seek(0)
    return buffer


# --- DUMMY DATA (FOR VIEWS) ---

# NOTE: The dashboard template expects a 'cloth_status' list. 
# We'll use the user's last 5 orders as a stand-in.
def get_cloth_status(user):
    # Fetch actual orders and format them
    orders = Order.objects.filter(user=user).select_related('shop').order_by('-id')[:5]
    if orders:
        result = []
        for order in orders:
            if order.payment_status != 'Completed':
                status = 'Payment Incomplete'
            else:
                status = order.cloth_status
            result.append({
                'cloth_name': f"Order #{order.id}",
                'status': status,
                'delivery_date': order.created_at,
                'shop_name': order.shop.name
            })
        return result
    return [
        {'cloth_name': 'No recent orders', 'status': 'N/A', 'delivery_date': 'N/A', 'shop_name': 'N/A'}
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

            # Send login success email only once per user
            try:
                profile = user.profile
                if not profile.login_email_sent:
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

                    # Mark that login email has been sent
                    profile.login_email_sent = True
                    profile.save()
            except Exception as e:
                # If profile doesn't exist or other error, continue without sending email
                pass

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
    # Statistics from your original code - Only count paid orders
    pending = Order.objects.filter(user=request.user, cloth_status="Pending", payment_status="Completed").count()
    completed = Order.objects.filter(user=request.user, cloth_status="Completed", payment_status="Completed").count()

    spent = Order.objects.filter(user=request.user, payment_status="Completed").aggregate(
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

    # Get only UNREAD notifications from database (avoid showing read notifications)
    recent_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False  # Only show unread notifications
    ).order_by('-created_at')[:5]

    # Format notifications for template (convert to dict format)
    recent_notifications = [
        {
            'id': notification.id,
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
        
    previous_shops = (
    LaundryShop.objects
    .filter(order__user=request.user, order__cloth_status='Completed', order__payment_status='Completed')
    .distinct()
)
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
        "previous_shops": previous_shops,   
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
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!

            send_email = form.cleaned_data.get('send_email', True)

            if send_email:
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
            else:
                messages.success(request, 'Your password was successfully updated!')

            return redirect('settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)
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
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a single notification as read."""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)


@login_required
def help_view(request):
    """Renders the Help page."""
    return render(request, 'help.html')



@login_required
def my_orders(request):
    """Renders the My Orders page."""
    # Show all orders, but modify status display for unpaid ones
    user_orders = Order.objects.filter(user=request.user).select_related('shop', 'branch').order_by('-created_at')

    # Add branch rating data and modify status for unpaid orders
    for order in user_orders:
        if order.branch:
            order.branch_rating = BranchRating.objects.filter(user=request.user, branch=order.branch).first()
        # Override cloth_status display if payment not completed
        if order.payment_status != 'Completed':
            order.display_status = 'Payment Incomplete'
        else:
            order.display_status = order.cloth_status

    return render(request, 'orders.html', {'orders': user_orders})


@login_required
def billing_payments(request):
    """Renders the Billing & Payments page."""
    # Only show orders with completed payment
    user_orders = Order.objects.filter(
        user=request.user,
        payment_status='Completed'  # Only show paid orders
    ).order_by('-created_at')
    return render(request, 'billing.html', {'orders': user_orders})

@login_required
def shop_detail(request, shop_id):
    """Renders a single laundry shop's detail page."""
    shop = get_object_or_404(LaundryShop, id=shop_id, is_approved=True)

    # Get all branches for this shop
    branches = Branch.objects.filter(shop=shop).prefetch_related('services')

    # Add rating data to each branch
    for branch in branches:
        branch_ratings = BranchRating.objects.filter(branch=branch)
        branch.average_rating = branch_ratings.aggregate(avg=Avg('rating'))['avg'] or 0
        branch.branch_ratings = branch_ratings

    # If shop has only one branch, redirect to branch detail
    if branches.count() == 1:
        return redirect('branch_detail', branch_id=branches.first().id)

    # Get all services across all branches
    all_services = Service.objects.filter(branch__shop=shop).select_related('branch')

    # Get shop ratings
    shop_ratings = ShopRating.objects.filter(shop=shop).select_related('user')
    user_rating = ShopRating.objects.filter(shop=shop, user=request.user).first()
    average_rating = shop_ratings.aggregate(avg=Avg('rating'))['avg'] or 0

    context = {
        'shop': shop,
        'branches': branches,
        'all_services': all_services,
        'shop_ratings': shop_ratings,
        'user_rating': user_rating,
        'average_rating': average_rating,
    }

    return render(request, 'shop_detail.html', context)


@login_required
def branch_detail(request, branch_id):
    """Renders a single branch's detail page."""
    branch = get_object_or_404(Branch, id=branch_id, shop__is_approved=True)

    # Get all services for this branch
    services = Service.objects.filter(branch=branch)

    # Get service ratings for the user
    for service in services:
        service.user_rating = ServiceRating.objects.filter(service=service, user=request.user).first()

    # Get branch ratings
    branch_ratings = BranchRating.objects.filter(branch=branch).select_related('user')
    user_rating = BranchRating.objects.filter(branch=branch, user=request.user).first()
    average_rating = branch_ratings.aggregate(avg=Avg('rating'))['avg'] or 0

    context = {
        'branch': branch,
        'shop': branch.shop,
        'services': services,
        'branch_ratings': branch_ratings,
        'user_rating': user_rating,
        'average_rating': average_rating,
    }

    return render(request, 'branch_detail.html', context)


@login_required
def select_branch_for_order(request, shop_id):
    """Customer selects a branch to place an order from."""
    shop = get_object_or_404(LaundryShop, id=shop_id, is_approved=True)

    branches = Branch.objects.filter(shop=shop).prefetch_related('services')

    # Add rating data to each branch
    for branch in branches:
        branch_ratings = BranchRating.objects.filter(branch=branch)
        branch.average_rating = branch_ratings.aggregate(avg=Avg('rating'))['avg'] or 0
        branch.branch_ratings = branch_ratings

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

    # Get all available clothes
    clothes = Cloth.objects.all().order_by('name')
    context['clothes'] = clothes

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

    # Calculate total amount and process clothes
    total_amount = 0
    order_items_data = []
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

            # Get selected clothes for this service
            clothes_list = request.POST.getlist(f'clothes_{service_id}')
            if not clothes_list:
                messages.error(request, f'Please select at least one type of cloth for {service.name}.')
                return redirect('select_services', shop_id=shop_id)

            # Process each cloth for this service
            service_total = 0
            for cloth_name in clothes_list:
                cloth_quantity = int(request.POST.get(f'quantity_{service_id}_{cloth_name}', 1))
                if cloth_quantity < 1:
                    cloth_quantity = 1

                try:
                    cloth = Cloth.objects.get(name=cloth_name)
                    order_items_data.append({
                        'service': service,
                        'cloth': cloth,
                        'quantity': cloth_quantity
                    })

                    # Get cloth-specific price
                    cloth_price_obj = ServiceClothPrice.objects.filter(service=service, cloth=cloth).first()
                    cloth_price = cloth_price_obj.price if cloth_price_obj else 0

                    service_total += cloth_price * cloth_quantity
                except Cloth.DoesNotExist:
                    continue

            # Add service total to overall total
            total_amount += service_total

        except (Service.DoesNotExist, ValueError):
            continue

    if total_amount == 0:
        messages.error(request, 'Unable to calculate order total. Please try again.')
        return redirect('select_services', shop_id=shop_id)

    if branch is None:
        messages.error(request, 'Unable to determine branch for order. Please try again.')
        return redirect('select_services', shop_id=shop_id)

    # Create order in database - linked to selected shop
    order = Order.objects.create(
        user=request.user,
        shop=shop,  # Order is linked to the selected shop
        branch=branch,
        amount=total_amount,
        cloth_status='Pending'
    )

    # Create OrderItem instances
    for item_data in order_items_data:
        OrderItem.objects.create(
            order=order,
            service=item_data['service'],
            cloth=item_data['cloth'],
            quantity=item_data['quantity']
        )

    # Log shop information for payment tracking
    print(f"Order #{order.id} created for shop: {shop.name} (ID: {shop.id})")

    # Store order items in session for later use (for PDF generation)
    request.session['order_items'] = []
    for item_data in order_items_data:
        request.session['order_items'].append({
            'service_name': item_data['service'].name,
            'cloth_name': item_data['cloth'].name,
            'quantity': item_data['quantity'],
            'price': float(item_data['service'].price) if item_data['service'].price else 0,
            'total': float(item_data['service'].price * item_data['quantity']) if item_data['service'].price else 0
        })
    request.session['order_id'] = order.id
    request.session['shop_id'] = shop.id

    # TEMPORARILY SKIP RAZORPAY - Store order details in session for later
    request.session['total_amount'] = float(total_amount)
    # We'll create Razorpay order later in the payment view

    # Note: Admin and shop email notifications removed as per requirements
    # Only the user receives the bill email after order creation

    # Send order confirmation bill to user
    try:
        # Generate PDF bill
        order_items = request.session.get('order_items', [])

        pdf_buffer = generate_payment_receipt_pdf(order, order_items)

        # Send bill email
        bill_message = f"""
Hi {order.user.get_full_name() or order.user.username},

Thank you for placing your order with Shine & Bright Laundry Services! 🧺✨

Your order has been successfully created and is now being processed.

Order Details:
- Order ID: #{order.id}
- Shop: {order.shop.name}
- Branch: {order.branch.name if order.branch else 'Main Branch'}
- Total Amount: ₹{order.amount}
- Status: {order.get_cloth_status_display()}

Delivery Information:
- Name: {order.delivery_name or 'To be provided'}
- Address: {order.delivery_address or 'To be provided'}
- Phone: {order.delivery_phone or 'To be provided'}

Please complete the payment to proceed with your order processing. You can make the payment using the secure payment gateway.

Please find your order bill attached as a PDF.

If you have any questions, feel free to contact us.

Thank you for choosing Shine & Bright!

Best regards,
Shine & Bright Team
🧺✨
"""

        # Create email with PDF attachment
        email = EmailMessage(
            subject=f"Order Bill - Order #{order.id}",
            body=bill_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[order.user.email],
        )

        # Attach PDF
        email.attach(f'order_bill_{order.id}.pdf', pdf_buffer.getvalue(), 'application/pdf')

        email.send(fail_silently=True)

    except Exception as e:
        # Log the error but don't fail the order process
        print(f"Failed to send order bill email: {e}")

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

    # If no order_items in session (for existing orders), create a dummy item
    if not order_items:
        order_items = [{
            'service': {'name': 'Laundry Service'},
            'quantity': 1,
            'total': total_amount
        }]

    # Create Razorpay order here instead of in create_order
    total_amount = request.session.get('total_amount', 0)
    
    # Get shop's Razorpay account ID (if linked) - Payment will go to this shop
    shop_account_id = order.shop.razorpay_account_id if hasattr(order.shop, 'razorpay_account_id') else None
    
    # Log payment routing information
    print(f"Payment for Order #{order.id} - Shop: {order.shop.name} (ID: {order.shop.id})")
    if shop_account_id:
        print(f"Shop has Razorpay account linked: {shop_account_id} - Payment will be transferred automatically")
    else:
        print(f"Shop Razorpay account not linked - Payment will stay with platform")

    try:
        # Create Razorpay order using utility function
        razorpay_order = create_razorpay_order(total_amount, shop_account_id)
        razorpay_order_id = razorpay_order['id']
        request.session['razorpay_order_id'] = razorpay_order_id
        
        # Store order ID in database for tracking
        order.razorpay_order_id = razorpay_order_id
        order.save()
    except Exception as e:
        messages.error(request, f'Unable to process payment at this time: {str(e)}')
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
    """Collect user delivery details and show payment section."""
    order_id = request.session.get('order_id')
    if not order_id:
        messages.error(request, 'No order found. Please start over.')
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id, user=request.user)
    show_payment = False
    razorpay_order_id = None

    if request.method == 'POST':
        form = UserDetailsForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, 'Delivery details saved successfully.')
            show_payment = True
            
            # Get order items from session
            order_items = request.session.get('order_items', [])
            total_amount = request.session.get('total_amount', order.amount)
            
            # Create Razorpay order
            shop_account_id = order.shop.razorpay_account_id if hasattr(order.shop, 'razorpay_account_id') else None
            
            try:
                razorpay_order = create_razorpay_order(total_amount, shop_account_id)
                razorpay_order_id = razorpay_order['id']
                request.session['razorpay_order_id'] = razorpay_order_id
                
                # Store order ID in database for tracking
                order.razorpay_order_id = razorpay_order_id
                order.save()
            except Exception as e:
                messages.error(request, f'Unable to process payment at this time: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserDetailsForm(instance=order)
        # Check if delivery details are already filled
        if order.delivery_name and order.delivery_address:
            show_payment = True
            # Get order items from session
            order_items = request.session.get('order_items', [])
            total_amount = request.session.get('total_amount', order.amount)
            
            # Create Razorpay order if not exists
            if not order.razorpay_order_id:
                shop_account_id = order.shop.razorpay_account_id if hasattr(order.shop, 'razorpay_account_id') else None
                try:
                    razorpay_order = create_razorpay_order(total_amount, shop_account_id)
                    razorpay_order_id = razorpay_order['id']
                    request.session['razorpay_order_id'] = razorpay_order_id
                    order.razorpay_order_id = razorpay_order_id
                    order.save()
                except Exception as e:
                    messages.error(request, f'Unable to process payment at this time: {str(e)}')
            else:
                razorpay_order_id = order.razorpay_order_id
                request.session['razorpay_order_id'] = razorpay_order_id

    # Get order items and total amount for payment section
    order_items = request.session.get('order_items', [])
    total_amount = request.session.get('total_amount', order.amount)
    
    # If no order_items in session, create a dummy item
    if not order_items:
        order_items = [{
            'service': {'name': 'Laundry Service'},
            'quantity': 1,
            'total': total_amount
        }]

    context = {
        'form': form,
        'order': order,
        'show_payment': show_payment,
        'order_items': order_items,
        'total_amount': total_amount,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'shop': order.shop,
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
    if not verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        messages.error(request, 'Payment verification failed. Please contact support.')
        return redirect('dashboard')

    # Payment verified, update order status and transfer funds
    order_id = request.session.get('order_id')
    if order_id:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Store payment details
        order.razorpay_payment_id = razorpay_payment_id
        order.razorpay_order_id = razorpay_order_id
        
        # Calculate commission and shop amount
        commission, shop_amount = calculate_commission(order.amount)
        order.platform_commission = commission
        order.shop_amount = shop_amount
        
        # Transfer payment to shop account (if shop has Razorpay account linked)
        # Payment goes to the shop that was selected when order was created
        shop_account_id = order.shop.razorpay_account_id if order.shop.razorpay_account_id else None
        
        # Log which shop is receiving the payment
        print(f"Processing payment transfer for Order #{order.id}")
        print(f"Shop: {order.shop.name} (ID: {order.shop.id})")
        print(f"Order Amount: ₹{order.amount}")
        print(f"Platform Commission: ₹{commission}")
        print(f"Shop Amount: ₹{shop_amount}")
        
        if shop_account_id:
            try:
                print(f"Transferring ₹{shop_amount} to shop account: {shop_account_id}")
                transfer_result = capture_payment_and_transfer(
                    razorpay_payment_id,
                    order.amount,
                    shop_account_id,  # Payment goes to the selected shop's account
                    commission_percentage=5  # 5% platform commission
                )
                
                if transfer_result['success']:
                    order.transfer_id = transfer_result.get('transfer_id')
                    order.transfer_status = transfer_result.get('transfer_status', 'completed')
                    print(f"✅ Payment successfully transferred to shop: {order.shop.name}")
                else:
                    order.transfer_status = transfer_result.get('transfer_status', 'failed')
                    # Log error but don't fail the order
                    print(f"❌ Transfer failed for order {order.id} to shop {order.shop.name}: {transfer_result.get('error')}")
            except Exception as e:
                # Log error but continue with order processing
                order.transfer_status = 'failed'
                print(f"❌ Error transferring payment for order {order.id} to shop {order.shop.name}: {str(e)}")
        else:
            # Shop doesn't have Razorpay account linked
            order.transfer_status = 'shop_account_not_linked'
            print(f"⚠️ Shop {order.shop.name} doesn't have Razorpay account linked. Payment held by platform.")
        
        order.cloth_status = 'Washing'  # Move to next status
        order.payment_status = 'Completed'  # Mark payment as completed
        order.save()

        # Create notification for user
        create_status_update_notification(order, 'Washing')

        # Generate PDF receipt
        order_items = request.session.get('order_items', [])
        if not order_items:
            # Fallback: get from OrderItem model
            order_items = []
            for item in order.order_items.all():
                order_items.append({
                    'service_name': item.service.name,
                    'cloth_name': item.cloth.name,
                    'quantity': item.quantity,
                    'price': float(item.service.price) if item.service.price else 0,
                    'total': float(item.service.price * item.quantity) if item.service.price else 0
                })

        pdf_buffer = generate_payment_receipt_pdf(order, order_items)

        # Send payment success email with PDF attachment
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

Please find your payment receipt attached as a PDF.

Thank you for choosing Shine & Bright!

Best regards,
Shine & Bright Team
🧺✨
"""

        try:
            # Create email with PDF attachment
            email = EmailMessage(
                subject=f"Payment Successful - Order #{order.id}",
                body=payment_success_message,
                from_email=settings.EMAIL_HOST_USER,
                to=[order.user.email],
            )

            # Attach PDF
            email.attach(f'payment_receipt_order_{order.id}.pdf', pdf_buffer.getvalue(), 'application/pdf')

            email.send(fail_silently=True)
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
    else:
        messages.error(request, 'No order found. Please start over.')
        return redirect('dashboard')


@login_required
def payment_failed(request):
    """Handle failed payment."""
    order_id = request.session.get('order_id')
    order = None
    if order_id:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        # Send payment failure email
        payment_failure_message = f"""
Hi {order.user.get_full_name() or order.user.username},

We regret to inform you that your payment for Order #{order.id} could not be processed at this time.

Order Details:
- Order ID: #{order.id}
- Shop: {order.shop.name}
- Amount: ₹{order.amount}

Possible reasons for payment failure:
- Insufficient funds in your account
- Payment gateway issues
- Network connectivity problems
- Card/payment method declined

You can try placing your order again or contact our support team for assistance.

For your security, please ensure:
- Your payment method has sufficient funds
- Your internet connection is stable
- Your payment details are entered correctly

Thank you for choosing Shine & Bright!

Best regards,
Shine & Bright Team
🧺✨
"""

        try:
            send_mail(
                subject=f"Payment Failed - Order #{order.id}",
                message=payment_failure_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[order.user.email],
                fail_silently=True,
            )
        except Exception as e:
            # Log the error but don't fail the payment failure process
            print(f"Failed to send payment failure email: {e}")

        # Delete the order since payment failed
        order.delete()

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
    now = timezone.now()

    delayed_orders = Order.objects.select_related(
        'user', 'shop'
    ).filter(
        delivery_date__isnull=False,
        delivery_date__lt=now,
        cloth_status__in=['Pending', 'Washing', 'Drying', 'Ironing']
    ).order_by('delivery_date')

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
        'delayed_orders': delayed_orders,
        'delayed_orders_count': delayed_orders.count(),
    }
    
    return render(request, 'admin_dashboard.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_update_order_status(request, order_id):
    """Update order status and/or shop assignment (AJAX endpoint)."""
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        new_shop_id = request.POST.get('shop_id')

        old_status = order.cloth_status
        old_shop = order.shop
        changes_made = []

        # Update status if provided
        if new_status and new_status in dict(Order.STATUS_CHOICES) and new_status != old_status:
            order.cloth_status = new_status
            changes_made.append(f"status to {new_status}")

        # Update shop if provided (only to approved shops)
        if new_shop_id:
            try:
                new_shop = LaundryShop.objects.get(id=new_shop_id, is_approved=True)
                if new_shop != old_shop:
                    order.shop = new_shop
                    # Reset branch when shop changes
                    order.branch = None
                    changes_made.append(f"shop to {new_shop.name}")
            except LaundryShop.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Invalid or unapproved shop selected'}, status=400)

        if changes_made:
            order.save()

            # Create notification for user
            create_status_update_notification(order, new_status)

            # Send notification emails
            try:
                # Email to Customer
                customer_subject = f"Order Updated - Order #{order.id}"
                customer_message = f"""
Hi {order.user.get_full_name() or order.user.username},

Your order has been updated!

Order Details:
- Order ID: #{order.id}
- Shop: {order.shop.name}
- Status: {order.cloth_status}
- Amount: ₹{order.amount}

Changes made: {', '.join(changes_made)}

Delivery Information:
- Name: {order.delivery_name or 'Not provided'}
- Address: {order.delivery_address or 'Not provided'}
- Phone: {order.delivery_phone or 'Not provided'}

{'Your laundry is ready for pickup!' if order.cloth_status == 'Ready' else ''}
{'Your order has been completed and delivered. Thank you for choosing us!' if order.cloth_status == 'Completed' else ''}

You can track your order status in your dashboard.

Best regards,
Shine & Bright Team
🧺✨
"""

                # Email to New Shop (if shop changed)
                if order.shop != old_shop:
                    new_shop_subject = f"Order Assigned to Your Shop - Order #{order.id}"
                    new_shop_message = f"""
Dear {order.shop.name} Team,

A new order has been assigned to your shop by an administrator.

Order Details:
- Order ID: #{order.id}
- Customer: {order.user.username} ({order.user.email})
- Status: {order.cloth_status}
- Amount: ₹{order.amount}

Please take appropriate action based on the current status.

Best regards,
Shine & Bright System
🧺✨
"""

                    send_mail(
                        subject=new_shop_subject,
                        message=new_shop_message,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[order.shop.email],
                        fail_silently=True,
                    )

                    # Email to Old Shop (if shop changed)
                    if old_shop != order.shop:
                        old_shop_subject = f"Order Reassigned - Order #{order.id}"
                        old_shop_message = f"""
Dear {old_shop.name} Team,

Order #{order.id} has been reassigned to another shop by an administrator.

Order Details:
- Order ID: #{order.id}
- Customer: {order.user.username}
- New Shop: {order.shop.name}

Best regards,
Shine & Bright System
🧺✨
"""

                        send_mail(
                            subject=old_shop_subject,
                            message=old_shop_message,
                            from_email=settings.EMAIL_HOST_USER,
                            recipient_list=[old_shop.email],
                            fail_silently=True,
                        )

                # Email to Shop for status updates
                elif new_status and new_status != old_status:
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
                print(f"Failed to send update emails: {e}")

            return JsonResponse({'success': True, 'message': f'Order updated successfully: {", ".join(changes_made)}'})
        else:
            return JsonResponse({'success': False, 'message': 'No changes made'}, status=400)

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

    # Only show orders from approved shops that are visible in admin dashboard
    approved_shops = LaundryShop.objects.filter(is_approved=True)

    # Filter orders to only show those from approved shops
    orders = orders.filter(shop__is_approved=True)

    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'current_status': status_filter,
        'search_query': search_query,
        'all_shops': approved_shops,  # Only approved shops for reassignment
    }

    return render(request, 'admin_orders.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_payments(request):
    """View all payments/orders with payment status filtering."""
    payment_status_filter = request.GET.get('payment_status', '')
    search_query = request.GET.get('search', '')

    orders = Order.objects.select_related('user', 'shop').order_by('-created_at')

    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)

    if search_query:
        orders = orders.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(id__icontains=search_query)
        )

    # Only show orders from approved shops
    orders = orders.filter(shop__is_approved=True)

    # Calculate total revenue for filtered orders
    total_revenue = orders.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'orders': orders,
        'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
        'current_payment_status': payment_status_filter,
        'search_query': search_query,
        'total_revenue': total_revenue,
    }

    return render(request, 'admin_orders.html', context)  # Reuse the same template


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_revenue_orders(request):
    """View orders sorted by revenue (amount) with filtering."""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')

    orders = Order.objects.select_related('user', 'shop').order_by('-amount')  # Sort by amount descending

    if status_filter:
        orders = orders.filter(cloth_status=status_filter)

    if search_query:
        orders = orders.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(id__icontains=search_query)
        )

    # Only show orders from approved shops
    orders = orders.filter(shop__is_approved=True)

    # Calculate total revenue for filtered orders
    total_revenue = orders.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'current_status': status_filter,
        'search_query': search_query,
        'total_revenue': total_revenue,
    }

    return render(request, 'admin_orders.html', context)  # Reuse the same template


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
def admin_open_shops(request):
    """View only open shops."""
    shops = LaundryShop.objects.filter(is_open=True).order_by('name')

    context = {
        'shops': shops,
    }

    return render(request, 'admin_shops.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_shop_detail(request, shop_id):
    """View detailed information about a specific shop."""
    shop = get_object_or_404(LaundryShop, id=shop_id)

    # Get branches and their services
    branches = Branch.objects.filter(shop=shop).prefetch_related('services')

    # Get recent orders
    recent_orders = Order.objects.filter(shop=shop).select_related('user', 'branch').order_by('-created_at')[:10]

    # Statistics
    total_orders = Order.objects.filter(shop=shop).count()
    completed_orders = Order.objects.filter(shop=shop, cloth_status='Completed').count()
    total_revenue = Order.objects.filter(shop=shop).aggregate(total=Sum('amount'))['total'] or 0

    # Shop ratings
    shop_ratings = ShopRating.objects.filter(shop=shop).select_related('user')
    average_rating = shop_ratings.aggregate(avg=Avg('rating'))['avg'] or 0

    context = {
        'shop': shop,
        'branches': branches,
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
        'shop_ratings': shop_ratings,
        'average_rating': average_rating,
    }

    return render(request, 'admin_shop_detail.html', context)


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
@login_required
@user_passes_test(is_staff_user, login_url='login')
def admin_edit_shop(request, shop_id):
    """Edit shop details (custom admin interface)."""
    shop = get_object_or_404(LaundryShop, id=shop_id)

    if request.method == 'POST':
        form = LaundryShopForm(request.POST, instance=shop)
        if form.is_valid():
            form.save()
            messages.success(request, 'Shop updated successfully.')
            return redirect('admin_shops')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LaundryShopForm(instance=shop)

    context = {
        'form': form,
        'shop': shop,
    }

    return render(request, 'admin_edit_shop.html', context)


# --- SHOP AUTHENTICATION VIEWS ---


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
                if not shop.is_open:
                    messages.error(request, "Your shop is currently closed. Please try again later.")
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
        branch_ratings = BranchRating.objects.filter(branch=branch)
        branch_average_rating = branch_ratings.aggregate(avg=Avg('rating'))['avg'] or 0
        branch_stats.append({
            'branch': branch,
            'total_orders': branch_orders.count(),
            'pending_orders': branch_orders.filter(cloth_status="Pending").count(),
            'completed_orders': branch_orders.filter(cloth_status="Completed").count(),
            'revenue': branch_orders.aggregate(total=Sum('amount'))['total'] or 0,
            'average_rating': branch_average_rating,
            'total_ratings': branch_ratings.count(),
        })

    # Generate shop notifications
    shop_notifications = []

    # Recent orders notifications
    recent_orders_for_notifications = Order.objects.filter(shop=shop).order_by('-created_at')[:10]
    now = timezone.now()

    delayed_orders = Order.objects.select_related(
        'user', 'branch'
    ).filter(
        shop=shop,
        delivery_date__isnull=False,
        delivery_date__lt=now,
        cloth_status__in=['Pending', 'Washing', 'Drying', 'Ironing']
    ).order_by('delivery_date')

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

    # Get shop ratings
    shop_ratings = ShopRating.objects.filter(shop=shop).select_related('user')
    average_rating = shop_ratings.aggregate(avg=Avg('rating'))['avg'] or 0

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
        'shop_ratings': shop_ratings,
        'average_rating': average_rating,
        'delayed_orders': delayed_orders,
        'delayed_orders_count': delayed_orders.count(),
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

    # Recent orders for this branch with cloth pricing details
    recent_orders = branch_orders.select_related('user').prefetch_related('order_items__service__cloth_prices', 'order_items__cloth')[:20]  # Show more orders on branch page

    # Get services with cloth prices for display
    services = branch.services.prefetch_related('cloths', 'cloth_prices').all()

    # Attach prices directly to cloth objects for easy template access
    for service in services:
        cloth_prices_dict = {}
        for cloth_price in service.cloth_prices.all():
            cloth_prices_dict[cloth_price.cloth.id] = cloth_price.price

        # Attach price to each cloth object
        for cloth in service.cloths.all():
            cloth.price = cloth_prices_dict.get(cloth.id)

    # Add cloth pricing details to each order
    for order in recent_orders:
        order.cloth_pricing_details = []
        for item in order.order_items.all():
            # Get the specific price for this cloth in this service
            cloth_price_obj = ServiceClothPrice.objects.filter(service=item.service, cloth=item.cloth).first()
            cloth_price = cloth_price_obj.price if cloth_price_obj else 0

            order.cloth_pricing_details.append({
                'service_name': item.service.name,
                'cloth_name': item.cloth.name,
                'quantity': item.quantity,
                'unit_price': cloth_price,
                'total_price': cloth_price * item.quantity
            })

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
        'services': services,
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

            # Create notification for user
            create_status_update_notification(order, new_status)

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


@shop_login_required
@require_POST
def toggle_shop_status(request):
    """Toggle shop open/closed status."""
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)

    is_open_str = request.POST.get('is_open', '').lower()
    is_open = is_open_str in ['true', '1', 'True']

    # Update shop status
    shop.is_open = is_open
    shop.save()

    status_text = "opened" if is_open else "closed"
    return JsonResponse({
        'success': True,
        'message': f'Shop has been {status_text} successfully!'
    })


@login_required
@require_POST
def rate_shop(request, shop_id):
    """Handle shop rating submission."""
    shop = get_object_or_404(LaundryShop, id=shop_id, is_approved=True)
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '').strip()

    if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
        return JsonResponse({'success': False, 'message': 'Invalid rating. Please select a rating between 1 and 5.'}, status=400)

    rating = int(rating)

    # Check if user already rated this shop
    existing_rating = ShopRating.objects.filter(user=request.user, shop=shop).first()
    if existing_rating:
        existing_rating.rating = rating
        existing_rating.comment = comment
        existing_rating.save()
        message = 'Your rating has been updated successfully!'
    else:
        ShopRating.objects.create(
            user=request.user,
            shop=shop,
            rating=rating,
            comment=comment
        )
        message = 'Thank you for rating this shop!'

    return JsonResponse({'success': True, 'message': message})


@login_required
@require_POST
def rate_service(request, service_id):
    """Handle service rating submission."""
    service = get_object_or_404(Service, id=service_id)
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '').strip()

    if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
        return JsonResponse({'success': False, 'message': 'Invalid rating. Please select a rating between 1 and 5.'}, status=400)

    rating = int(rating)

    # Check if user already rated this service
    existing_rating = ServiceRating.objects.filter(user=request.user, service=service).first()
    if existing_rating:
        existing_rating.rating = rating
        existing_rating.comment = comment
        existing_rating.save()
        message = 'Your rating has been updated successfully!'
    else:
        ServiceRating.objects.create(
            user=request.user,
            service=service,
            rating=rating,
            comment=comment
        )
        message = 'Thank you for rating this service!'

    return JsonResponse({'success': True, 'message': message})


@login_required
@require_POST
def rate_branch(request, branch_id):
    """Handle branch rating submission."""
    branch = get_object_or_404(Branch, id=branch_id, shop__is_approved=True)
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '').strip()

    if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
        return JsonResponse({'success': False, 'message': 'Invalid rating. Please select a rating between 1 and 5.'}, status=400)

    rating = int(rating)

    # Check if user already rated this branch
    existing_rating = BranchRating.objects.filter(user=request.user, branch=branch).first()
    if existing_rating:
        existing_rating.rating = rating
        existing_rating.comment = comment
        existing_rating.save()
        message = 'Your rating has been updated successfully!'
    else:
        BranchRating.objects.create(
            user=request.user,
            branch=branch,
            rating=rating,
            comment=comment
        )
        message = 'Thank you for rating this branch!'

    return JsonResponse({'success': True, 'message': message})

def shop_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            shop = LaundryShop.objects.get(email=email)
        except LaundryShop.DoesNotExist:
            messages.error(request, "Shop not found")
            return redirect("shop_reset_request")

        token = str(uuid.uuid4())
        ShopPasswordResetToken.objects.create(shop=shop, token=token)

        reset_link = f"http://localhost:8000/shop/reset/{token}/"

        send_mail(
            "Shop Password Reset - Shine & Bright",
            f"Click to reset your password:\n{reset_link}",
            settings.EMAIL_HOST_USER,
            [email],
        )

        messages.success(request, "Reset link sent to email")
        return redirect("shop_login")

    return render(request, "shop_reset_request.html")

def shop_reset_confirm(request, token):
    try:
        token_obj = ShopPasswordResetToken.objects.get(token=token)
        shop = token_obj.shop
    except ShopPasswordResetToken.DoesNotExist:
        return HttpResponse("Invalid or expired link")

    if token_obj.is_expired():
        token_obj.delete()
        return HttpResponse("Reset link expired")

    if request.method == "POST":
        new_password = request.POST.get("password")
        shop.set_password(new_password)
        shop.save()
        token_obj.delete()
        messages.success(request, "Password updated successfully!")
        return redirect("shop_login")

    return render(request, "shop_reset_confirm.html", {"token": token})

def newsletter_subscribe(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            messages.error(request, "Email is required")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        # Save subscriber
        subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)

        if not created:
            messages.warning(request, "You are already subscribed!")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        # Get approved shops (limit 3)
        shops = LaundryShop.objects.filter(is_approved=True)[:3]

        # Email content
        subject = "Welcome to Shine & Bright – Shop Details Inside 🧺✨"
        html_message = render_to_string(
            "emails/newsletter_shop_details.html",
            {"shops": shops}
        )

        email_message = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        email_message.content_subtype = "html"
        email_message.send(fail_silently=True)

        messages.success(request, "Subscribed successfully! Shop details sent to your email.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # 🚫 Block changes if already completed
    if order.cloth_status == "Completed":
        return JsonResponse({
            "success": False,
            "message": "Completed orders cannot be modified."
        })

    new_status = request.POST.get("status")
    order.cloth_status = new_status
    order.save()

    # Create notification for user
    create_status_update_notification(order, new_status)

    return JsonResponse({
        "success": True
    })


@shop_login_required
def shop_bank_details(request):
    """Shop can view and edit their bank details."""
    shop_id = request.session.get('shop_id')
    shop = get_object_or_404(LaundryShop, id=shop_id)

    if request.method == 'POST':
        form = ShopBankDetailsForm(request.POST, instance=shop)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bank details updated successfully!')
            return redirect('shop_bank_details')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ShopBankDetailsForm(instance=shop)

    # Check if bank details are complete
    has_bank_details = all([
        shop.bank_account_holder_name,
        shop.bank_account_number,
        shop.bank_ifsc_code,
        shop.bank_name,
    ])

    context = {
        'shop': shop,
        'form': form,
        'has_bank_details': has_bank_details,
    }

    return render(request, 'shop_bank_details.html', context)
