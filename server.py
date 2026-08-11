import os
import subprocess
from flask import Flask, request, jsonify, send_from_directory, send_file
import whisper
from deep_translator import GoogleTranslator

app = Flask(__name__)

OUTPUT_DIR = r"C:\Users\Tejeswari\.n8n-files"

print("Loading Universal Whisper AI Speech Model...")
whisper_model = whisper.load_model("small")
print("Whisper Model loaded successfully!")

# Multi-Language Voice Pools (Exclusively Female Voices)
VOICE_POOLS = {
    "English": [
        "en-US-JennyNeural", "en-US-AriaNeural", "en-US-MichelleNeural",
        "en-GB-SoniaNeural", "en-AU-NatashaNeural", "en-US-AnaNeural"
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
# Video Dubbing Pipeline (Replaces Video Audio & Synthesizes Dub)
# ------------------------------------------------------------------
@app.route('/process-video', methods=['POST'])
def process_video():
    global latest_translation
    try:
        if not request.data:
            return jsonify({"error": "No binary data received"}), 400
        
        target_lang = request.headers.get('Target-Language', 'Telugu')
        print(f"\n[TARGET LANGUAGE]: {target_lang}")

        input_video_path = os.path.join(OUTPUT_DIR, "input.mp4")
        output_audio_path = os.path.join(OUTPUT_DIR, "output.mp3")
        merged_audio_path = os.path.join(OUTPUT_DIR, "combined_speech.mp3")
        output_dubbed_video = os.path.join(OUTPUT_DIR, "final_dubbed.mp4")
        
        segment_files = []

        # Remove previous output video if exists
        if os.path.exists(output_dubbed_video):
            os.remove(output_dubbed_video)
        
        with open(input_video_path, "wb") as f:
            f.write(request.data)
            
        # Step 1: Extract Audio
        print("[1/4] Extracting audio stream...")
        ffmpeg_extract = f'ffmpeg -y -i "{input_video_path}" -vn -ac 1 -ar 16000 "{output_audio_path}"'
        subprocess.run(ffmpeg_extract, shell=True, check=True)

        # Step 2: Transcribe Dialogue
        print("[2/4] Analyzing dialogue lines with Whisper AI...")
        result = whisper_model.transcribe(output_audio_path)
        segments = result.get('segments', [])

        if not segments:
            return jsonify({"status": "success", "message": "No speech found."}), 200

        full_text_log = []
        voice_pool = VOICE_POOLS.get(target_lang, VOICE_POOLS["Telugu"])

        # Step 3: Translate & Synthesize Audio
        print(f"[3/4] Translating and synthesizing female voice tracks in {target_lang}...")
        for idx, seg in enumerate(segments):
            original_text = seg['text'].strip()
            if not original_text:
                continue

            # Translate to Telugu if selected
            if target_lang == "Telugu":
                try:
                    translated_text = GoogleTranslator(source='auto', target='te').translate(original_text)
                except Exception as e:
                    print(f"Translation error: {e}")
                    translated_text = original_text
            else:
                translated_text = original_text

            voice = voice_pool[idx % len(voice_pool)]
            seg_audio_path = os.path.join(OUTPUT_DIR, f"seg_{idx}.mp3")
            
            # Clean quotes for safe command execution
            safe_text = translated_text.replace('"', '').replace("'", "")
            tts_cmd = f'edge-tts --voice "{voice}" --text "{safe_text}" --write-media "{seg_audio_path}"'
            subprocess.run(tts_cmd, shell=True, check=True)
            segment_files.append(seg_audio_path)
            
            speaker_num = (idx % len(voice_pool)) + 1
            full_text_log.append(f"<b>[Speaker {speaker_num} - Female Voice ({voice.split('-')[2]})]:</b> {translated_text}")

        # Combine synthesized audio clips
        concat_list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
        with open(concat_list_path, "w", encoding='utf-8') as f:
            for seg_file in segment_files:
                f.write(f"file '{seg_file}'\n")

        concat_cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_list_path}" -c copy "{merged_audio_path}"'
        subprocess.run(concat_cmd, shell=True, check=True)

        # Step 4: Map Video Stream + New Dubbed Audio Stream (Replaces original English audio)
        print("[4/4] Replacing original audio track with dubbed audio in video...")
        merge_cmd = f'ffmpeg -y -i "{input_video_path}" -i "{merged_audio_path}" -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest "{output_dubbed_video}"'
        subprocess.run(merge_cmd, shell=True, check=True)

        # Cleanup temporary audio segments
        for seg_f in segment_files:
            if os.path.exists(seg_f):
                os.remove(seg_f)

        latest_translation = "<br>".join(full_text_log)
        print("[SUCCESS]: Processing complete!\n")

        return jsonify({"status": "success", "message": "Video processed!"}), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-result', methods=['GET'])
def get_result():
    global latest_translation
    dubbed_video_path = os.path.join(OUTPUT_DIR, "final_dubbed.mp4")
    merged_audio_path = os.path.join(OUTPUT_DIR, "combined_speech.mp3")
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
    merged_audio_path = os.path.join(OUTPUT_DIR, "combined_speech.mp3")
    if os.path.exists(merged_audio_path):
        return send_file(merged_audio_path, mimetype='audio/mpeg', as_attachment=True, download_name='translated_audio_female.mp3')
    return jsonify({"error": "Audio file not found"}), 404

if __name__ == '__main__':
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    app.run(port=5000, debug=True)