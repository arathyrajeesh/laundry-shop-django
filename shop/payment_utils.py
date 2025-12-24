"""
Payment utility functions for Razorpay Connect (Marketplace Payments)
Handles split payments between platform and shops
"""
import razorpay
from django.conf import settings
from decimal import Decimal


def get_razorpay_client(shop_key_id=None, shop_key_secret=None):
    """Get Razorpay client instance."""
    if shop_key_id and shop_key_secret:
        return razorpay.Client(auth=(shop_key_id, shop_key_secret))
    else:
        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def calculate_commission(order_amount, commission_percentage=5):
    """
    Calculate platform commission.
    Default commission: 5% of order amount
    
    Args:
        order_amount: Total order amount
        commission_percentage: Platform commission percentage (default: 5%)
    
    Returns:
        tuple: (commission_amount, shop_amount)
    """
    order_amount = Decimal(str(order_amount))
    commission_percentage = Decimal(str(commission_percentage))
    
    commission = (order_amount * commission_percentage) / 100
    shop_amount = order_amount - commission
    
    return commission, shop_amount


def create_razorpay_order(amount, shop_account_id=None, shop_key_id=None, shop_key_secret=None):
    """
    Create Razorpay order for payment.

    Args:
        amount: Order amount in rupees
        shop_account_id: Shop's Razorpay account ID (for marketplace payments)
        shop_key_id: Shop's Razorpay key ID (for shop-specific payments)
        shop_key_secret: Shop's Razorpay key secret (for shop-specific payments)

    Returns:
        dict: Razorpay order response
    """
    client = get_razorpay_client(shop_key_id, shop_key_secret)
    
    # Convert amount to paisa (Razorpay uses smallest currency unit)
    amount_in_paisa = int(float(amount) * 100)
    
    order_data = {
        'amount': amount_in_paisa,
        'currency': 'INR',
        'payment_capture': '1',  # Auto capture
    }
    
    # If shop has Razorpay account, use it for marketplace payments
    if shop_account_id:
        # For Razorpay Connect, we need to create order with transfers
        # This will be handled in payment capture
        pass
    
    try:
        razorpay_order = client.order.create(order_data)
        return razorpay_order
    except Exception as e:
        raise Exception(f"Failed to create Razorpay order: {str(e)}")


def capture_payment_and_transfer(payment_id, order_amount, shop_account_id, commission_percentage=5, shop_key_id=None, shop_key_secret=None):
    """
    Capture payment and transfer to shop account (Razorpay Connect).

    Note: Payment is already captured automatically (payment_capture='1' in order creation).
    This function only handles the transfer to shop account.

    Args:
        payment_id: Razorpay payment ID
        order_amount: Total order amount
        shop_account_id: Shop's Razorpay account ID
        commission_percentage: Platform commission percentage
        shop_key_id: Shop's Razorpay key ID
        shop_key_secret: Shop's Razorpay key secret

    Returns:
        dict: Transfer details
    """
    client = get_razorpay_client(shop_key_id, shop_key_secret)
    
    # Calculate amounts
    commission, shop_amount = calculate_commission(order_amount, commission_percentage)
    
    # Convert to paisa
    shop_amount_paisa = int(float(shop_amount) * 100)
    
    try:
        # Transfer to shop account using Razorpay Connect
        if shop_account_id:
            # For Razorpay Connect, create transfer from payment
            # Format: client.payment.transfer(payment_id, transfer_data)
            transfer_data = {
                'transfers': [
                    {
                        'account': shop_account_id,  # Shop's Razorpay account ID
                        'amount': shop_amount_paisa,
                        'currency': 'INR',
                    }
                ]
            }
            
            # Create transfer
            transfer = client.payment.transfer(payment_id, transfer_data)
            
            # Handle response - transfer can be a list or dict
            if isinstance(transfer, list) and len(transfer) > 0:
                transfer_obj = transfer[0]
            else:
                transfer_obj = transfer
            
            return {
                'success': True,
                'transfer_id': transfer_obj.get('id') if isinstance(transfer_obj, dict) else None,
                'transfer_status': transfer_obj.get('status', 'pending') if isinstance(transfer_obj, dict) else 'completed',
                'shop_amount': shop_amount,
                'commission': commission,
            }
        else:
            # If shop doesn't have Razorpay account, payment stays with platform
            # Shop can withdraw manually later
            return {
                'success': True,
                'transfer_id': None,
                'transfer_status': 'shop_account_not_linked',
                'shop_amount': shop_amount,
                'commission': commission,
                'message': 'Shop Razorpay account not linked. Payment held by platform.',
            }
    except razorpay.errors.BadRequestError as e:
        # Handle case where shop account is not linked or invalid
        error_msg = str(e)
        return {
            'success': False,
            'error': error_msg,
            'transfer_status': 'failed',
            'shop_amount': shop_amount,
            'commission': commission,
        }
    except razorpay.errors.ServerError as e:
        # Handle server errors
        return {
            'success': False,
            'error': f'Razorpay server error: {str(e)}',
            'transfer_status': 'failed',
            'shop_amount': shop_amount,
            'commission': commission,
        }
    except Exception as e:
        # Handle other exceptions
        return {
            'success': False,
            'error': f'Transfer error: {str(e)}',
            'transfer_status': 'failed',
            'shop_amount': shop_amount,
            'commission': commission,
        }


def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature, shop_key_id=None, shop_key_secret=None):
    """
    Verify Razorpay payment signature.

    Args:
        razorpay_order_id: Razorpay order ID
        razorpay_payment_id: Razorpay payment ID
        razorpay_signature: Razorpay signature
        shop_key_id: Shop's Razorpay key ID
        shop_key_secret: Shop's Razorpay key secret

    Returns:
        bool: True if signature is valid
    """
    client = get_razorpay_client(shop_key_id, shop_key_secret)
    
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
    except Exception:
        return False


def get_payment_details(payment_id, shop_key_id=None, shop_key_secret=None):
    """
    Get payment details from Razorpay.

    Args:
        payment_id: Razorpay payment ID
        shop_key_id: Shop's Razorpay key ID
        shop_key_secret: Shop's Razorpay key secret

    Returns:
        dict: Payment details
    """
    client = get_razorpay_client(shop_key_id, shop_key_secret)
    
    try:
        payment = client.payment.fetch(payment_id)
        return payment
    except Exception as e:
        raise Exception(f"Failed to fetch payment details: {str(e)}")

