from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
        path("", views.hero, name="home"),
        path("login/", views.login_page, name="login"),
        path("signup/", views.signup, name="signup"),
        path("logout/", views.logout_user, name="logout"),

        # PROFILE
        path("profile/", views.profile_page, name="profile"),
        path("profile/edit/", views.edit_profile, name="edit_profile"),

        # DASHBOARD
        path("dashboard/", views.user_dashboard, name="dashboard"),
        path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter_subscribe"),


        # SHOPS
        path("shop/<int:shop_id>/", views.shop_detail, name="shop_detail"),
        path("shop/<int:shop_id>/select-branch/", views.select_branch_for_order, name="select_branch_for_order"),
        path("shop/<int:shop_id>/select-services/", views.select_services, name="select_services"),
        path("shop/<int:shop_id>/branch/<int:branch_id>/select-services/", views.select_services, name="select_services_branch"),
        path("shop/<int:shop_id>/create-order/", views.create_order, name="create_order"),
        path("user-details/", views.user_details, name="user_details"),
        path("payment/", views.payment, name="payment"),
        path("payment/success/", views.payment_success, name="payment_success"),
        path("payment/failed/", views.payment_failed, name="payment_failed"),
        path("branch/<int:branch_id>/", views.branch_detail, name="branch_detail"),

        # DROPDOWN PAGES
        path("settings/", views.settings_view, name="settings"),
        path("settings/change-password/", views.change_password, name="change_password"),
        path("settings/privacy-policy/", views.privacy_policy, name="privacy_policy"),
        path("settings/delete-account/", views.delete_account, name="delete_account"),
        path("help/", views.help_view, name="help"),
        path("notifications/", views.notifications_view, name="notifications"),
        path("notifications/mark-read/", views.mark_notifications_read, name="mark_notifications_read"),
        path("orders/", views.my_orders, name="orders"),
        path("billing/", views.billing_payments, name="billing"),

        # ADMIN DASHBOARD
        path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
        path("admin-panel/orders/", views.admin_orders, name="admin_orders"),
        path("admin-panel/orders/revenue/", views.admin_revenue_orders, name="admin_revenue_orders"),
        path("admin-panel/payments/", views.admin_payments, name="admin_payments"),
        path("admin-panel/users/", views.admin_users, name="admin_users"),
        path("admin-panel/shops/", views.admin_shops, name="admin_shops"),
        path("admin-panel/shops/open/", views.admin_open_shops, name="admin_open_shops"),
        path("admin-panel/shop/<int:shop_id>/approve/", views.admin_approve_shop, name="admin_approve_shop"),
        path("admin-panel/shop/<int:shop_id>/reject/", views.admin_reject_shop, name="admin_reject_shop"),
        path("admin-panel/shop/<int:shop_id>/edit/", views.admin_edit_shop, name="admin_edit_shop"),
        path("admin-panel/shop/<int:shop_id>/", views.admin_shop_detail, name="admin_shop_detail"),
        path("admin-panel/order/<int:order_id>/update-status/", views.admin_update_order_status, name="admin_update_order_status"),

        # SHOP AUTHENTICATION
        path("shop/register/", views.shop_register, name="shop_register"),
        path("shop/login/", views.shop_login, name="shop_login"),
        path("shop/logout/", views.shop_logout, name="shop_logout"),
        path("shop/dashboard/", views.shop_dashboard, name="shop_dashboard"),
        path("shop/notifications/", views.shop_notifications, name="shop_notifications"),
        path("shop/select-branch/", views.select_branch, name="select_branch"),
        path("shop/branch/<int:branch_id>/orders/", views.branch_orders, name="branch_orders"),
        path("shop/order/<int:order_id>/update-status/", views.shop_update_order_status, name="shop_update_order_status"),
        # Branch & Service URLs (shop-level)
        path('shop/branch/add/', views.add_branch, name='add_branch'),
        path('shop/branch/<int:branch_id>/edit/', views.edit_branch, name='edit_branch'),
        path('shop/branch/<int:branch_id>/delete/', views.delete_branch, name='delete_branch'),

        # Service: can pass branch_id to auto-attach after create
        path('shop/service/add/', views.add_service, name='add_service'),
        path("service/add/<int:branch_id>/", views.add_service, name="add_service_branch"),
        path('shop/service/<int:service_id>/edit/', views.edit_service, name='edit_service'),
        path('shop/service/<int:service_id>/delete/', views.delete_service, name='delete_service'),

        # Shop status toggle
        path('shop/toggle-shop-status/', views.toggle_shop_status, name='toggle_shop_status'),

        # Ratings
        path("shop/<int:shop_id>/rate/", views.rate_shop, name="rate_shop"),
        path("service/<int:service_id>/rate/", views.rate_service, name="rate_service"),
        path("branch/<int:branch_id>/rate/", views.rate_branch, name="rate_branch"),
        path("password_reset/",
                auth_views.PasswordResetView.as_view(
                        template_name="password_reset.html",
                        email_template_name="password_reset_email.html",
                        subject_template_name="password_reset_subject.txt",
                ),
                name="password_reset"
                ),


        path("password_reset_done/",
                auth_views.PasswordResetDoneView.as_view(template_name="password_reset_done.html"),
                name="password_reset_done"),

        path("reset/<uidb64>/<token>/",
                auth_views.PasswordResetConfirmView.as_view(template_name="password_reset_confirm.html"),
                name="password_reset_confirm"),

        path("reset/done/",
                auth_views.PasswordResetCompleteView.as_view(template_name="password_reset_complete.html"),
                name="password_reset_complete"),
        path("shop/reset/", views.shop_reset_request, name="shop_reset_request"),
        path("shop/reset/<str:token>/", views.shop_reset_confirm, name="shop_reset_confirm"),

]
