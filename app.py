# app.py (production)
from flask import Flask, jsonify, request
from flask_cors import CORS
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse, Dial, Say
import os
import logging
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS to allow edge devices on specific ports
def is_allowed_origin(origin):
    """Check if origin is from allowed ports"""
    if not origin:
        return False
    # Allow localhost and any hostname on ports 8080-8081
    allowed_patterns = [
        ':8080',
        ':8081'
    ]
    return any(pattern in origin for pattern in allowed_patterns)

CORS(app, resources={
    r"/api/*": {
        "origins": is_allowed_origin,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_API_KEY = os.environ.get('TWILIO_API_KEY')
TWILIO_API_SECRET = os.environ.get('TWILIO_API_SECRET')
TWILIO_TWIML_APP_SID = os.environ.get('TWILIO_TWIML_APP_SID')

# Validate configuration
required_vars = [
    'TWILIO_ACCOUNT_SID',
    'TWILIO_API_KEY',
    'TWILIO_API_SECRET',
    'TWILIO_TWIML_APP_SID'
]

for var in required_vars:
    if not os.environ.get(var):
        logger.error(f'Missing required environment variable: {var}')


@app.route('/api/twilio-token', methods=['GET', 'OPTIONS'])
def get_token():
    """Generate Twilio access token for browser calling"""
    try:
        logger.info('Generating Twilio access token')
        
        token = AccessToken(
            TWILIO_ACCOUNT_SID,
            TWILIO_API_KEY,
            TWILIO_API_SECRET,
            identity=f'hmi-user-{int(datetime.now().timestamp())}',
            ttl=3600
        )

        voice_grant = VoiceGrant(
            outgoing_application_sid=TWILIO_TWIML_APP_SID,
            incoming_allow=False
        )

        token.add_grant(voice_grant)
        
        logger.info('Token generated successfully')
        return jsonify({'token': token.to_jwt()})

    except Exception as e:
        logger.error(f'Error generating token: {str(e)}')
        return jsonify({'error': 'Failed to generate token'}), 500
    
@app.route('/api/twilio-voice', methods=['POST'])
def handle_voice():
    """Twilio calls this URL to get instructions"""
    
    # Twilio sends form data with the call details
    to_number = request.form.get('To')  # The number you want to call
    from_number = request.form.get('From')  # "client:hmi-user-123"
    
    # Create TwiML response (XML instructions)
    response = VoiceResponse()

    say = Say("Connecting you to Outrun support.", voice='alice', language='en-US')
    response.append(say)

    # Tell Twilio to dial the number
    dial = Dial(caller_id="+14086419333")  # Your Twilio number
    dial.number(to_number)  # The support number
    response.append(dial)
    
    # Return XML to Twilio
    return str(response), 200, {'Content-Type': 'text/xml'}


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

def main():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()