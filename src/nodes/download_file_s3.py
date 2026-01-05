from ..client_s3 import get_s3_instance
S3_INSTANCE = get_s3_instance()
import os

class DownloadFileS3:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required":{
                "s3_path": ("STRING", {"default": "input/example.png"}),
                "local_path": ("STRING", {"default": "input/example.png"}),
            }
        }
    
    CATEGORY = "ComfyS3"
    INPUT_NODE = True
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("local_path",)
    FUNCTION = "download_file_s3"
    
    def download_file_s3(self, s3_path, local_path):
        local_path = S3_INSTANCE.download_file(s3_path=s3_path, local_path=local_path)
        print(f"Downloaded file from S3 to {local_path}")
        return (local_path,)
    
class EasyDownloadFileS3:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required":{
                "s3_path": ("STRING", {"default": "input/example.png"}),
            }
        }
    
    CATEGORY = "ComfyS3"
    INPUT_NODE = True
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("local_path",)
    FUNCTION = "download_file_s3"
    
    def download_file_s3(self, s3_path):
        # Ensure temp directory exists
        temp_dir = "input/temp"
        os.makedirs(temp_dir, exist_ok=True)

        filename = os.path.basename(s3_path)
        temp_path = os.path.join(temp_dir, filename)

        # Download
        local_path = S3_INSTANCE.download_file(
            s3_path=s3_path,
            local_path=temp_path
        )

        print(f"[ComfyS3] Downloaded {s3_path} -> {local_path}")

        return (local_path,)