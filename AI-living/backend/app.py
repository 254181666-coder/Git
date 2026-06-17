from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from modules import AvatarDriver, AudioDriver, ChatBot, LivePlay

load_dotenv()

app = Flask(__name__)
CORS(app)

avatar_driver = AvatarDriver()
audio_driver = AudioDriver()
chatbot = ChatBot()
live_play = LivePlay()

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': '播助手服务运行正常'})

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        'openai_base_url': os.getenv('OPENAI_BASE_URL', ''),
        'has_api_key': bool(os.getenv('OPENAI_API_KEY'))
    })

@app.route('/api/avatar/mode', methods=['POST'])
def set_avatar_mode():
    data = request.json
    mode = data.get('mode', 'camera')
    avatar_driver.set_mode(mode)
    return jsonify({'success': True, 'mode': mode})

@app.route('/api/avatar/camera/start', methods=['POST'])
def start_camera():
    data = request.json
    camera_id = data.get('camera_id', 0)
    avatar_driver.start_camera(camera_id)
    return jsonify({'success': True})

@app.route('/api/avatar/camera/stop', methods=['POST'])
def stop_camera():
    avatar_driver.stop_camera()
    return jsonify({'success': True})

@app.route('/api/audio/clips', methods=['POST'])
def load_audio_clips():
    data = request.json
    clips = data.get('clips', [])
    audio_driver.load_audio_clips(clips)
    return jsonify({'success': True})

@app.route('/api/audio/mode', methods=['POST'])
def set_audio_mode():
    data = request.json
    mode = data.get('mode', 'random')
    audio_driver.set_play_mode(mode)
    return jsonify({'success': True, 'mode': mode})

@app.route('/api/audio/split', methods=['POST'])
def split_audio():
    data = request.json
    input_path = data.get('input_path')
    output_dir = data.get('output_dir')
    segments = audio_driver.split_audio(input_path, output_dir)
    return jsonify({'success': True, 'segments': segments})

@app.route('/api/chat/product', methods=['POST'])
def set_product_info():
    data = request.json
    info = data.get('info', '')
    chatbot.set_product_info(info)
    return jsonify({'success': True})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    response = chatbot.chat(message)
    return jsonify({'success': True, 'response': response})

@app.route('/api/live/video', methods=['POST'])
def load_video():
    data = request.json
    video_path = data.get('video_path')
    live_play.load_video(video_path)
    return jsonify({'success': True})

@app.route('/api/live/deduplicate', methods=['POST'])
def deduplicate_frame():
    import base64
    import cv2
    import numpy as np
    data = request.json
    frame_data = data.get('frame')
    
    nparr = np.frombuffer(base64.b64decode(frame_data), np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    processed = live_play.remove_duplicate(frame)
    
    _, buffer = cv2.imencode('.jpg', processed)
    result = base64.b64encode(buffer).decode('utf-8')
    return jsonify({'success': True, 'frame': result})

@app.route('/api/live/timestamp', methods=['GET'])
def get_timestamp():
    ts = live_play.get_timestamp()
    return jsonify({'success': True, 'timestamp': ts})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
