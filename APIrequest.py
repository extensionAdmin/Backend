
from flask import Flask, send_file, jsonify
from dubbing_utils import download_dubbed_file, wait_for_dubbing_completion
from elevenlabs.client import ElevenLabs
from typing import Optional
from moviepy.editor import VideoFileClip
import youtube_dl
import os
from decouple import config
from tempfile import NamedTemporaryFile
from moviepy.editor import VideoFileClip

app = Flask(__name__)

ELEVENLABS_API_KEY = ""+config('API_VAR')
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

def create_dub_from_file(file_path: str, source_language: str, target_language: str) -> Optional[str]:
    # Load the video
    video_data = VideoFileClip(file_path)

    # Save to a temporary file -------
    with NamedTemporaryFile(delete=False, suffix='.mp4',dir='/tmp') as temp_file:
        # Write the video to the temporary file
        video_data.write_videofile(temp_file.name, codec='libx264')
        temp_file_path = temp_file.name  # Get the path of the temporary file -----

    # Open the temporary file for reading
    with open(temp_file_path, 'rb') as temp_file:
        # Upload the local file for dubbing
        response = client.dubbing.dub_a_video_or_an_audio_file(
            file=temp_file,  # Pass the file object
            target_lang=target_language,
            source_lang=source_language,
            num_speakers=1,
            watermark=True,
        )

    # Clean up the temporary file
    os.remove(temp_file_path)

    dubbing_id = response.dubbing_id
    if wait_for_dubbing_completion(dubbing_id):
        output_file_path = download_dubbed_file(dubbing_id, target_language)
        return output_file_path
    else:
        return None


def download_dailymotion_video(url: str, output_path: str = "./") -> str:
    """
    Downloads a video from Dailymotion using the given URL.
    
    Args:
        url (str): The Dailymotion video URL.
        output_path (str): The directory where the video will be saved. Default is the current directory.
        
    Returns:
        str: The file path of the downloaded video.
    """
    # Ensure the output folder exists
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Define options for youtube_dl
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),  # Set the output template
        'format': 'best',  # Download the best available quality
    }
    
    # Download the video using youtube_dl
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)  # Extracts and downloads the video
        video_file_path = ydl.prepare_filename(info_dict)  # Get the downloaded file path
    
    return os.path.normpath(video_file_path)



def find_video_file(data_folder):
    """
    Searches for the first .mp4 video file within a dynamic folder structure under the specified data folder.

    :param data_folder: The path to the 'data' folder.
    :return: The full path to the video file if found, otherwise None.
    """
    for root, dirs, files in os.walk(data_folder):
        for file in files:
            if file.endswith('.mp4'):  # Check for .mp4 files
                return os.path.join(root, file)  # Return the full path to the video file
    
    return None  # Return None if no video file is found

#video_path = find_video_file(data_folder)
def translate_video_file(file_path, source_language, target_language):
    try:
        print(f"Translating video: {file_path} from {source_language} to {target_language}")
        result = create_dub_from_file(file_path, source_language, target_language)
        
        if result:
            print(f"Translation result: {result}")
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted the original file: {file_path}")
            
            video_file_path = find_video_file('data')
            if not video_file_path:
                print("Translated video file not found.")
                return {"error": "Translated video file not found."}
                
            print(f"Translated video sent: {video_file_path}")
            return {"translated_file": video_file_path}
        else:
            print("Dubbing failed or timed out.")
            return {"error": "Dubbing failed or timed out."}
    except Exception as e:
        print(f"An error occurred during video translation: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}

    


