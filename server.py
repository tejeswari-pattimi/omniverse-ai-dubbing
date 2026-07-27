import os
import subprocess
from flask import Flask, request, jsonify, send_from_directory, send_file
import whisper

app = Flask(__name__)

OUTPUT_DIR = r"C:\Users\Tejeswari\.n8n-files"

print("Loading Universal Whisper AI Speech Model...")
whisper_model = whisper.load_model("small")
print("Whisper Model loaded successfully!")

EXPANDED_VOICE_POOL = [
    "en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-EricNeural",
    "en-US-JennyNeural", "en-US-AriaNeural", "en-US-AnaNeural"
]

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

# ------------------------------------------------------------------
# Multi-Voice + Automated Lip-Sync Pipeline
# ------------------------------------------------------------------
@app.route('/process-video', methods=['POST'])
def process_video():
    global latest_translation
    try:
        if not request.data:
            return jsonify({"error": "No binary data received"}), 400
        
        input_video_path = os.path.join(OUTPUT_DIR, "input.mp4")
        output_audio_path = os.path.join(OUTPUT_DIR, "output.mp3")
        merged_audio_path = os.path.join(OUTPUT_DIR, "combined_speech.mp3")
        temp_dubbed_video = os.path.join(OUTPUT_DIR, "temp_dubbed.mp4")
        final_lipsynced_video = os.path.join(OUTPUT_DIR, "final_dubbed.mp4")
        
        segment_files = []

        for fpath in [final_lipsynced_video, temp_dubbed_video]:
            if os.path.exists(fpath):
                os.remove(fpath)
        
        with open(input_video_path, "wb") as f:
            f.write(request.data)
            
        # Step 1: Extract Audio
        print("\n[1/5] Extracting audio stream...")
        ffmpeg_extract = f'ffmpeg -y -i "{input_video_path}" -vn -ac 1 -ar 16000 "{output_audio_path}"'
        subprocess.run(ffmpeg_extract, shell=True, check=True)

        # Step 2: Transcribe & Segment Dialogue
        print("[2/5] Analyzing dialogue and assigning voices...")
        result = whisper_model.transcribe(output_audio_path, task="translate")
        segments = result.get('segments', [])

        if not segments:
            return jsonify({"status": "success", "message": "No speech found."}), 200

        full_text_log = []

        # Step 3: Multi-Speaker TTS Generation
        for idx, seg in enumerate(segments):
            text = seg['text'].strip()
            if not text:
                continue

            voice = EXPANDED_VOICE_POOL[idx % len(EXPANDED_VOICE_POOL)]
            seg_audio_path = os.path.join(OUTPUT_DIR, f"seg_{idx}.mp3")
            
            tts_cmd = f'edge-tts --voice "{voice}" --text "{text}" --write-media "{seg_audio_path}"'
            subprocess.run(tts_cmd, shell=True, check=True)
            segment_files.append(seg_audio_path)
            
            full_text_log.append(f"<b>[Speaker {idx + 1} - {voice.split('-')[2]}]:</b> {text}")

        # Combine audio tracks
        concat_list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
        with open(concat_list_path, "w") as f:
            for seg_file in segment_files:
                f.write(f"file '{seg_file}'\n")

        concat_cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_list_path}" -c copy "{merged_audio_path}"'
        subprocess.run(concat_cmd, shell=True, check=True)

       # Step 4: Stitch multi-voice audio back into video
        print(f"[4/4] Stitching multi-voice track into final video...")
        merge_cmd = f'ffmpeg -y -i "{input_video_path}" -i "{merged_audio_path}" -c:v copy -c:a aac -map 0:v -map 1:a -shortest "{output_dubbed_video}"'
        subprocess.run(merge_cmd, shell=True, check=True)

        # === NEW AUTO-CLEANUP ROUTINE ===
        print("Cleaning up intermediate audio/video segments to save disk space...")
        # Delete temporary segment files
        for seg_file in segment_files:
            if os.path.exists(seg_file):
                os.remove(seg_file)
        
        # Delete extra temporary files
        for temp_file in [output_audio_path, merged_audio_path, concat_list_path]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        # ================================

        latest_translation = "<br>".join(full_text_log)
        print("[SUCCESS]: Multi-speaker dubbing complete and storage cleaned!\n")

        # Step 5: AI Lip-Sync Pass (Wav2Lip)
        checkpoint_path = os.path.join(OUTPUT_DIR, "wav2lip.pth")
        if os.path.exists(checkpoint_path):
            print("[5/5] Applying AI Lip-Syncing model (Wav2Lip)...")
            lipsync_cmd = f'python inference.py --checkpoint_path "{checkpoint_path}" --face "{input_video_path}" --audio "{merged_audio_path}" --outfile "{final_lipsynced_video}"'
            subprocess.run(lipsync_cmd, shell=True, check=True)
        else:
            print("[5/5] Wav2Lip model checkpoint not found. Using standard audio overlay.")
            os.rename(temp_dubbed_video, final_lipsynced_video)

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
    return jsonify({"translation": latest_translation, "has_video": os.path.exists(dubbed_video_path)})

@app.route('/get-video', methods=['GET'])
def get_video():
    dubbed_video_path = os.path.join(OUTPUT_DIR, "final_dubbed.mp4")
    if os.path.exists(dubbed_video_path):
        response = send_file(dubbed_video_path, mimetype='video/mp4')
        response.headers["Accept-Ranges"] = "bytes"
        return response
    return jsonify({"error": "Video file not found"}), 404

if __name__ == '__main__':
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    app.run(port=5000, debug=True)