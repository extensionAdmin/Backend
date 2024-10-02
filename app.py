
from flask import Flask,request,jsonify,send_file
from flask_cors import CORS
import os
import shutil
import threading
from APIrequest import download_dailymotion_video,translate_video_file
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "chrome-extension://dngffmokoiolbhdcpnhgmplpmaepdcmd"}})

results = {}


# Worker function to handle video processing in the background
def process_video(video_url, oLang, tLang, task_id):
    with app.app_context():  # Push the application context for Flask
        try:
            print(f"Starting video processing for task {task_id}...")

            # Download video
            downloaded_video_path = download_dailymotion_video(video_url)
            print(f"Downloaded video to {downloaded_video_path} for task {task_id}")
            
            # Translate the video
            translation_result = translate_video_file(downloaded_video_path, oLang, tLang)
            print(f"Translated video for task {task_id}, result: {translation_result}")

            # Store the result in the results dictionary
            results[task_id] = {"translated_file": translation_result}

            # Clean up after processing
            """"""

            print(f"Video processing completed for task {task_id}")

        except Exception as e:
            print(f"Error processing video for task {task_id}: {str(e)}")
            results[task_id] = {"error": str(e)}


@app.route('/send-url', methods=['POST'])
def send_url():
    data = request.get_json()  # Get the JSON data sent in the POST request
    video_url = data.get('url')  # Extract the URL from the JSON
    oLang = data.get('oLang')
    tLang = data.get('tLang')
    # Create a unique task ID based on the request data (e.g., using hash)
    task_id = data.get('task_id')
    
    video_thread = threading.Thread(target=process_video, args=(video_url, oLang, tLang, task_id))
    video_thread.start()
    # Return the task ID to the client so they can check the status later
    return jsonify({"message": "Video processing started", "task_id": task_id}), 202
    
@app.route('/check-status/<task_id>', methods=['GET'])
def check_status(task_id):
    result = results.get(task_id)  # Safely get the result

    if result:
        # Task exists
        if 'error' in result:
            return jsonify({"error": result['error']}), 500

        # Ensure you're accessing the correct file path from within the dict
        translated_file_path_dict = result.get('translated_file')
        
        # Check if translated_file_path_dict is a dict
        if isinstance(translated_file_path_dict, dict):
            # Extract the actual file path string from the 'translated_file' key
            translated_file_path = translated_file_path_dict.get('translated_file')
        else:
            translated_file_path = translated_file_path_dict
        
        # Check if it's a string
        if isinstance(translated_file_path, str):
        
            if os.path.exists(translated_file_path):
                print("file sent")
                response = send_file(translated_file_path, as_attachment=True)
                delete_Data()
                clearTemp_data()
                response.call_on_close(lambda: delete_after_sending(translated_file_path))
                return response
            else:
                print(f"File not found: {translated_file_path}")
                return jsonify({"error": "Translated file not found"}), 404
        else:
            print(f"Translated file path is not a string, it's: {type(translated_file_path)}")
            return jsonify({"error": "Invalid file path format"}), 500

    # If the task is still running or task_id not found
    return jsonify({"message": "Video processing still in progress"}), 200



   
def delete_Data():
    data_folder = 'data'  # Get the parent directory
    if os.path.exists(data_folder):
        shutil.rmtree(data_folder)
    
def clearTemp_data():
    data_folder = '/tmp'  # Access the /tmp folder

    # Iterate over the files in /tmp and remove them
    for filename in os.listdir(data_folder):
        file_path = os.path.join(data_folder, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)  # Delete file
                print(f'{file_path} deleted.')
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")  # Return error if file removal fails

def delete_after_sending(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted translated file: {file_path}")
    except Exception as e:
        print(f"Error deleting file: {str(e)}")


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))

