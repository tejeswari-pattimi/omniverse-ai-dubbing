import os
import gc
import subprocess
from flask import Flask, request, jsonify, send_from_directory, send_file
import speech_recognition as sr
from deep_translator import GoogleTranslator

app = Flask(__name__)

OUTPUT_DIR = os.path.join(os.getcwd(), "output_files")

VOICE_POOLS = {
    "English": [
        "en-US-JennyNeural", "en-US-AriaNeural", "en-US-MichelleNeural"
    ],
    "Telugu": [
        "te-IN-ShrutiNeural"  # Female Telugu Voice
    ]
}

latest_translation = ""

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

# ------------------------------------------------------------------
# Video Dubbing Pipeline via Lightweight Cloud APIs
# ------------------------------------------------------------------
@app.route('/process-video', methods=['POST'])
def process_video():
    global latest_translation
    try:
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        if not request.data:
            return jsonify({"error": "No binary data received"}), 400
        
        target_lang = request.headers.get('Target-Language', 'Telugu')
        print(f"\n[TARGET LANGUAGE]: {target_lang}")

        input_video_path = os.path.join(OUTPUT_DIR, "input.mp4")
        extracted_audio_wav = os.path.join(OUTPUT_DIR, "extracted.wav")
        merged_audio_path = os.path.join(OUTPUT_DIR, "combined_speech.mp3")
        output_dubbed_video = os.path.join(OUTPUT_DIR, "final_dubbed.mp4")

        if os.path.exists(output_dubbed_video):
            os.remove(output_dubbed_video)
        
        with open(input_video_path, "wb") as f:
            f.write(request.data)
            
        # Step 1: Extract Audio Stream
        print("[1/4] Extracting audio stream...")
        ffmpeg_extract = f'ffmpeg -y -i "{input_video_path}" -vn -ac 1 -ar 16000 "{extracted_audio_wav}"'
        subprocess.run(ffmpeg_extract, shell=True, check=True)

        # Step 2: Transcribe via Cloud Speech API
        print("[2/4] Transcribing dialogue with Speech Recognition API...")
        recognizer = sr.Recognizer()
        with sr.AudioFile(extracted_audio_wav) as source:
            audio_data = recognizer.record(source)
            original_text = recognizer.recognize_google(audio_data)

        if not original_text.strip():
            return jsonify({"status": "success", "message": "No speech found."}), 200

        print(f"Transcribed Text: {original_text}")

        # Step 3: Translate to Telugu
        print(f"[3/4] Translating to {target_lang}...")
        if target_lang == "Telugu":
            translated_text = GoogleTranslator(source='auto', target='te').translate(original_text)
        else:
            translated_text = original_text

        # Step 4: Synthesize Audio & Merge Video
        voice = VOICE_POOLS["Telugu"][0]
        temp_tts_audio = os.path.join(OUTPUT_DIR, "tts_speech.mp3")
        safe_text = translated_text.replace('"', '').replace("'", "")
        
        tts_cmd = f'edge-tts --voice "{voice}" --text "{safe_text}" --write-media "{temp_tts_audio}"'
        subprocess.run(tts_cmd, shell=True, check=True)

        merge_cmd = f'ffmpeg -y -i "{input_video_path}" -i "{temp_tts_audio}" -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest "{output_dubbed_video}"'
        subprocess.run(merge_cmd, shell=True, check=True)

        latest_translation = f"<b>[Speaker - Female Voice (Shruti)]:</b> {translated_text}"
        print("[SUCCESS]: Processing complete!\n")

        gc.collect()
        return jsonify({"status": "success", "message": "Video processed!"}), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        gc.collect()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-result', methods=['GET'])
def get_result():
    global latest_translation
    dubbed_video_path = os.path.join(OUTPUT_DIR, "final_dubbed.mp4")
    merged_audio_path = os.path.join(OUTPUT_DIR, "tts_speech.mp3")
    return jsonify({
        "translation": latest_translation, 
        "has_video": os.path.exists(dubbed_video_path),
        "has_audio": os.path.exists(merged_audio_path)
    })

@app.route('/get-video', methods=['GET'])
def get_video():
    dubbed_video_path = os.path.join(OUTPUT_DIR, "final_dubbed.mp4")
    if os.path.exists(dubbed_video_path):
        return send_file(dubbed_video_path, mimetype='video/mp4', as_attachment=True, download_name='final_dubbed_video.mp4')
    return jsonify({"error": "Video file not found"}), 404

@app.route('/get-audio', methods=['GET'])
def get_audio():
    merged_audio_path = os.path.join(OUTPUT_DIR, "tts_speech.mp3")
    if os.path.exists(merged_audio_path):
        return send_file(merged_audio_path, mimetype='audio/mpeg', as_attachment=True, download_name='translated_audio_female.mp3')
    return jsonify({"error": "Audio file not found"}), 404

if __name__ == '__main__':
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)