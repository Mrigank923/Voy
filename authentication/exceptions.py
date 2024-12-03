from rest_framework.views import exception_handler
from rest_framework.exceptions import Throttled

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if isinstance(exc, Throttled):
        custom_response_data = {
            'success': False,
            'message': f'Request was throttled. Expected available in {int(exc.wait)} seconds.'
        }
        response.data = custom_response_data
    
    return response
