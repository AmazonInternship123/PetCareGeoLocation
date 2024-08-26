import os
import logging
import requests
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAPMYINDIA_API_KEY = os.getenv('MAPMYINDIA_API_KEY')

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return handler_input.request_envelope.request.type == "LaunchRequest"

    def handle(self, handler_input):
        speech_text = "Welcome to the Find Nearest Vet skill. You can ask me to find the nearest veterinarian."
        return handler_input.response_builder.speak(speech_text).ask(speech_text).get_response()

class FindVetIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("FindVetIntent")(handler_input)
    
    def handle(self, handler_input):
        device_id = handler_input.request_envelope.context.system.device.device_id
        api_endpoint = handler_input.request_envelope.context.system.api_endpoint
        api_access_token = handler_input.request_envelope.context.system.api_access_token

        address_url = f"{api_endpoint}/v1/devices/{device_id}/settings/address"
        headers = {"Authorization": f"Bearer {api_access_token}"}
        
        try:
            response = requests.get(address_url, headers=headers)
            response.raise_for_status()
            address = response.json()
            
            if not address or "latitude" not in address or "longitude" not in address:
                speech_text = "I couldn't retrieve your location. Please ensure you have provided location permissions."
                return handler_input.response_builder.speak(speech_text).get_response()
            
            latitude = address["latitude"]
            longitude = address["longitude"]
            
            vets = find_nearby_vets(latitude, longitude)
            
            if not vets:
                speech_text = "I couldn't find any nearby veterinarians."
            else:
                closest_vet = vets[0]
                speech_text = f"The closest vet is {closest_vet['name']}, located at {closest_vet['address']}."
            
            return handler_input.response_builder.speak(speech_text).get_response()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching address: {e}")
            speech_text = "There was an error retrieving your address."
            return handler_input.response_builder.speak(speech_text).get_response()

def find_nearby_vets(latitude, longitude):
    url = f"https://apis.mapmyindia.com/advancedmaps/v1/{MAPMYINDIA_API_KEY}/places/search/json?query=veterinary&location={latitude},{longitude}&radius=5000"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        places = response.json().get("results", [])
        
        vets = [
            {"name": place["name"], "address": place["formatted_address"]}
            for place in places
        ]
        
        return vets
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching vets: {e}")
        return []

sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(FindVetIntentHandler())

def lambda_handler(event, context):
    return sb.lambda_handler()(event, context)
