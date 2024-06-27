import os
import subprocess
import json

def extract_metadata(file_path):
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext in ['.mp3', '.mp4', '.avi', '.mov', '.mkv']:
        return extract_media_metadata(file_path)
    else:
        raise ValueError("Unsupported file type")

def extract_media_metadata(file_path):
    try:
        cmd = f"ffprobe -v quiet -print_format json -show_format -show_streams \"{file_path}\""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        probe = json.loads(result.stdout)
        format_metadata = probe['format']
        
        metadata = {
            "title": format_metadata.get('tags', {}).get('title', os.path.basename(file_path)),
            "date": format_metadata.get('tags', {}).get('creation_time', None),
            "duration": float(format_metadata.get('duration', 0)),
            "tags": format_metadata.get('tags', {})
        }
        return metadata
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return {}

def process_files(file_paths):
    metadata_list = []
    for file_path in file_paths:
        try:
            metadata = extract_metadata(file_path)
            metadata_list.append({"file_path": file_path, "metadata": metadata})
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    return metadata_list

# Example usage with multiple files
file_paths = [
    "The Universe in 4 Minutes.mp4"
]

metadata_list = process_files(file_paths)
for item in metadata_list:
    print(f"Metadata for {item['file_path']}: {item['metadata']}")
