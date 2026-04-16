"""
Standardized error response handling for BiblioDrift API
This module provides consistent error response formatting across all API endpoints.
"""

from flask import jsonify
from typing import Optional, Dict, Any


# Error code constants
class ErrorCodes:
    """Standard error codes used across the API"""
    # Validation errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_FIELDS = "MISSING_FIELDS"
    INVALID_JSON = "INVALID_JSON"
    INVALID_INPUT = "INVALID_INPUT"
    
    # Authentication errors (401)
    AUTH_ERROR = "AUTH_ERROR"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    
    # Authorization errors (403)
    FORBIDDEN = "FORBIDDEN"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    
    # Not found errors (404)
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"
    
    # Conflict errors (409)
    CONFLICT = "CONFLICT"
    RESOURCE_EXISTS = "RESOURCE_EXISTS"
    
    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Server errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    # Service unavailable (503)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


def error_response(
    code: str,
    message: str,
    status_code: int = 400,
    additional_data: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Generate a standardized error response.
    
    Args:
        code: Error code from ErrorCodes class
        message: Human-readable error message
        status_code: HTTP status code (default: 400)
        additional_data: Optional additional data to include in response
        
    Returns:
        Tuple of (jsonify response, status_code)
        
    Example:
        return error_response(
            ErrorCodes.VALIDATION_ERROR,
            "Title is required",
            400
        )
    """
    response_data = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    
    # Add any additional data (e.g., retry_after for rate limiting)
    if additional_data:
        response_data["error"].update(additional_data)
    
    return jsonify(response_data), status_code


def success_response(
    data: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    status_code: int = 200
) -> tuple:
    """
    Generate a standardized success response.
    
    Args:
        data: Response data
        message: Optional success message
        status_code: HTTP status code (default: 200)
        
    Returns:
        Tuple of (jsonify response, status_code)
        
    Example:
        return success_response(
            data={"books": books_list},
            message="Books retrieved successfully"
        )
    """
    response_data = {
        "success": True
    }
    
    if message:
        response_data["message"] = message
    
    if data:
        response_data.update(data)
    
    return jsonify(response_data), status_code


# Convenience functions for common errors
def validation_error(message: str, status_code: int = 400) -> tuple:
    """Return a validation error response"""
    return error_response(ErrorCodes.VALIDATION_ERROR, message, status_code)


def missing_fields_error(fields: str) -> tuple:
    """Return a missing fields error response"""
    return error_response(
        ErrorCodes.MISSING_FIELDS,
        f"Missing required fields: {fields}",
        400
    )


def invalid_json_error() -> tuple:
    """Return an invalid JSON error response"""
    return error_response(
        ErrorCodes.INVALID_JSON,
        "Invalid JSON or missing request body",
        400
    )


def auth_error(message: str = "Invalid credentials") -> tuple:
    """Return an authentication error response"""
    return error_response(ErrorCodes.INVALID_CREDENTIALS, message, 401)


def forbidden_error(message: str = "Access forbidden") -> tuple:
    """Return a forbidden error response"""
    return error_response(ErrorCodes.FORBIDDEN, message, 403)


def unauthorized_access_error(message: str = "Unauthorized access") -> tuple:
    """Return an unauthorized access error response"""
    return error_response(ErrorCodes.UNAUTHORIZED_ACCESS, message, 403)


def not_found_error(resource: str = "Resource") -> tuple:
    """Return a not found error response"""
    return error_response(
        ErrorCodes.NOT_FOUND,
        f"{resource} not found",
        404
    )


def resource_exists_error(resource: str = "Resource") -> tuple:
    """Return a resource already exists error response"""
    return error_response(
        ErrorCodes.RESOURCE_EXISTS,
        f"{resource} already exists",
        409
    )


def rate_limit_error(retry_after: int) -> tuple:
    """Return a rate limit exceeded error response"""
    response = error_response(
        ErrorCodes.RATE_LIMIT_EXCEEDED,
        "Rate limit exceeded. Try again shortly.",
        429,
        additional_data={"retry_after": retry_after}
    )
    # Add Retry-After header
    json_response, status_code = response
    json_response.headers['Retry-After'] = str(retry_after)
    return json_response, status_code


def internal_error(message: str = "An internal error occurred") -> tuple:
    """Return an internal server error response"""
    return error_response(ErrorCodes.INTERNAL_ERROR, message, 500)


def service_unavailable_error(message: str = "Service temporarily unavailable") -> tuple:
    """Return a service unavailable error response"""
    return error_response(ErrorCodes.SERVICE_UNAVAILABLE, message, 503)
