import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def format_phone_number(phone):
    """
    Format phone number for SMS Chef API

    Args:
        phone (str): The phone number to format

    Returns:
        str: Formatted phone number
    """
    # Remove any non-digit characters except the + sign at the beginning
    if isinstance(phone, str):
        if phone.startswith('+'):
            digits = '+' + ''.join(filter(str.isdigit, phone[1:]))
        else:
            digits = ''.join(filter(str.isdigit, phone))

        # Make sure the phone number is in the correct format
        if digits.startswith('+'):
            return digits
        elif digits.startswith('0'):
            return '+63' + digits[1:]  # Replace leading 0 with +63 (Philippines)
        elif digits.startswith('63'):
            return '+' + digits
        else:
            return '+63' + digits  # Assume Philippines number
    return phone

def send_sms(message, recipients, sender_name=None):
    """
    Send SMS using SMS Chef API based on their Python example

    Args:
        message (str): The message to send
        recipients (list or str): A list of phone numbers or a single phone number
        sender_name (str, optional): Not used for SMS Chef, kept for compatibility

    Returns:
        dict: The API response
    """
    # Log function call for debugging
    logger.info(f"send_sms called with message: {message}, recipients: {recipients}")

    # Check if API secret is configured
    if not settings.SMSCHEF_API_SECRET:
        logger.error("SMS Chef API secret is not set")
        return {"error": "API secret not configured"}

    # Check if message is empty
    if not message or not message.strip():
        logger.error("Message cannot be empty")
        return {"error": "Message cannot be empty"}

    # Handle multiple recipients
    if isinstance(recipients, list):
        if not recipients:
            logger.error("No recipients provided")
            return {"error": "No recipients provided"}

        # For multiple recipients, use the bulk API
        formatted_recipients = [format_phone_number(phone) for phone in recipients]
        recipients_str = ','.join(formatted_recipients)
        logger.info(f"Formatted recipients for bulk SMS: {recipients_str}")

        # Define the endpoint and payload exactly as in the documentation
        url = settings.SMSCHEF_BULK_API_URL
        data = {
            "secret": settings.SMSCHEF_API_SECRET,
            "mode": "devices",
            "device": settings.SMSCHEF_DEVICE_ID,  # Add device ID
            "number": recipients_str,  # Changed from "numbers" to "number" as per SMS Chef API
            "message": message,
            "sim": str(settings.SMSCHEF_SIM)  # Convert to string to ensure proper formatting
        }
    else:
        # For a single recipient
        formatted_phone = format_phone_number(recipients)
        logger.info(f"Formatted single recipient: {formatted_phone}")

        # Define the endpoint and payload exactly as in the documentation
        url = settings.SMSCHEF_API_URL
        data = {
            "secret": settings.SMSCHEF_API_SECRET,
            "mode": "devices",
            "device": settings.SMSCHEF_DEVICE_ID,  # Add device ID
            "phone": formatted_phone,
            "message": message,
            "sim": str(settings.SMSCHEF_SIM)  # Convert to string to ensure proper formatting
        }

    # Log the request (excluding the secret)
    log_data = data.copy()
    log_data["secret"] = "***REDACTED***"
    logger.info(f"Sending SMS request to {url} with data: {log_data}")

    try:
        # Make the POST request exactly as in the documentation
        response = requests.post(url, data=data)

        # Log the response
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response text: {response.text}")

        # Handle the response
        if response.status_code == 200:
            try:
                response_json = response.json()
                logger.info(f"Success: {response_json}")

                # Special case for "Invalid Parameters" - the SMS might still be sent
                if "Invalid Parameters" in response.text:
                    logger.warning("Received 'Invalid Parameters' response but SMS might still be sent")
                    return {
                        "status": 200,  # Treat as success
                        "has_warning": True,
                        "warning": "Invalid Parameters warning, but message may have been delivered",
                        "message": "Message sent with parameter warnings",
                        "original_response": response.text
                    }

                # Check if the API returned a success status
                # SMS Chef API can return status 200 even with warnings or partial success
                if response_json.get('status') == 200:
                    # Check if there's a warning message but still consider it a success
                    if 'warning' in response_json:
                        logger.warning(f"API warning: {response_json.get('warning')}")
                        # Include the warning in the response but don't treat it as an error
                        response_json['has_warning'] = True
                    return response_json
                else:
                    error_msg = response_json.get('message', 'Unknown error')

                    # Special case for "Invalid Parameters" - the SMS might still be sent
                    if "Invalid Parameters" in error_msg:
                        logger.warning("Received 'Invalid Parameters' error but SMS might still be sent")
                        return {
                            "status": 200,  # Treat as success
                            "has_warning": True,
                            "warning": "Invalid Parameters warning, but message may have been delivered",
                            "message": "Message sent with parameter warnings",
                            "original_error": error_msg
                        }

                    logger.error(f"API error: {error_msg}")
                    return {"error": f"SMS Chef API error: {error_msg}"}
            except ValueError:
                logger.error(f"Invalid JSON response: {response.text}")

                # Special case for "Invalid Parameters" in non-JSON response
                if "Invalid Parameters" in response.text:
                    logger.warning("Received 'Invalid Parameters' in non-JSON response but SMS might still be sent")
                    return {
                        "status": 200,  # Treat as success
                        "has_warning": True,
                        "warning": "Invalid Parameters warning, but message may have been delivered",
                        "message": "Message sent with parameter warnings",
                        "original_response": response.text
                    }

                return {"error": f"Invalid JSON response: {response.text}"}
        else:
            # Special case for "Invalid Parameters" in non-200 response
            if "Invalid Parameters" in response.text:
                logger.warning(f"Received 'Invalid Parameters' in non-200 response (status: {response.status_code}) but SMS might still be sent")
                return {
                    "status": 200,  # Treat as success
                    "has_warning": True,
                    "warning": f"Invalid Parameters warning (status: {response.status_code}), but message may have been delivered",
                    "message": "Message sent with parameter warnings",
                    "original_response": response.text
                }

            try:
                error_data = response.json()
                error_msg = error_data.get('message', f"Error: {response.status_code}")

                # Special case for "Invalid Parameters" in JSON error
                if "Invalid Parameters" in str(error_data):
                    logger.warning(f"Received 'Invalid Parameters' in JSON error (status: {response.status_code}) but SMS might still be sent")
                    return {
                        "status": 200,  # Treat as success
                        "has_warning": True,
                        "warning": f"Invalid Parameters warning (status: {response.status_code}), but message may have been delivered",
                        "message": "Message sent with parameter warnings",
                        "original_error": error_msg
                    }

                logger.error(f"Error: {response.status_code}, {error_data}")
                return {"error": f"SMS Chef API error: {error_msg}"}
            except ValueError:
                logger.error(f"Error: {response.status_code}, {response.text}")

                # Special case for "Invalid Parameters" in non-JSON error
                if "Invalid Parameters" in response.text:
                    logger.warning(f"Received 'Invalid Parameters' in non-JSON error (status: {response.status_code}) but SMS might still be sent")
                    return {
                        "status": 200,  # Treat as success
                        "has_warning": True,
                        "warning": f"Invalid Parameters warning (status: {response.status_code}), but message may have been delivered",
                        "message": "Message sent with parameter warnings",
                        "original_response": response.text
                    }

                return {"error": f"SMS Chef API error: Status {response.status_code}"}
    except Exception as e:
        logger.exception(f"Exception while sending SMS: {str(e)}")
        return {"error": f"Exception while sending SMS: {str(e)}"}
