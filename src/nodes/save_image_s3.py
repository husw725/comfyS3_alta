import os
import json
import tempfile
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from comfy.cli_args import args

from ..client_s3 import get_s3_instance
S3_INSTANCE = get_s3_instance()


class SaveImageS3:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        self.temp_dir = os.path.join(base_dir, "temp/")
        self.s3_output_dir = os.getenv("S3_OUTPUT_DIR")
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "images": ("IMAGE", ),
            "filename_prefix": ("STRING", {"default": "Image"})},
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
                }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("s3_image_paths",)
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)
    CATEGORY = "ComfyS3"

    def save_images(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = S3_INSTANCE.get_save_path(filename_prefix, images[0].shape[1], images[0].shape[0])
        results = list()
        s3_image_paths = list()
        
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))
            
            file = f"{filename}_{counter:05}_.png"
            temp_file = None
            try:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                    temp_file_path = temp_file.name
                    
                    # Save the image to the temporary file
                    img.save(temp_file_path, pnginfo=metadata, compress_level=self.compress_level)

                    # Upload the temporary file to S3
                    s3_path = os.path.join(full_output_folder, file)
                    file_path = S3_INSTANCE.upload_file(temp_file_path, s3_path)

                    # Add the s3 path to the s3_image_paths list
                    s3_image_paths.append(file_path)
                    
                    # Add the result to the results list
                    results.append({
                        "filename": file,
                        "subfolder": subfolder,
                        "type": self.type
                    })
                    counter += 1

            finally:
                # Delete the temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        return { "ui": { "images": results },  "result": (s3_image_paths,) }


class SaveImageWithBucketPathS3:
    def __init__(self):
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "s3_paths": ("STRING", {"default": "my-bucket/path/to/file.png"}),  # 可以传入单个路径或列表
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("s3_image_paths",)
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)
    CATEGORY = "ComfyS3"

    def save_images(self, images, s3_paths, prompt=None, extra_pnginfo=None):
        """
        images: list of tensors
        s3_paths: str or list[str] 对应每张图片的完整 S3 路径（桶/路径/文件名）
        """
        if isinstance(s3_paths, str):
            s3_paths = [s3_paths] * len(images)  # 单路径应用到所有图片

        if len(s3_paths) != len(images):
            raise ValueError("images 和 s3_paths 数量不一致！")

        s3_image_paths = []
        results = []

        for img_tensor, s3_path in zip(images, s3_paths):
            # 转成 PIL Image
            i = 255. * img_tensor.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            temp_file_path = None
            try:
                # 创建临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                    temp_file_path = temp_file.name
                    img.save(temp_file_path, pnginfo=metadata, compress_level=self.compress_level)

                    # 上传到 S3
                    file_path = S3_INSTANCE.upload_file(temp_file_path, s3_path)
                    s3_image_paths.append(file_path)

                    # 添加 ui 显示信息
                    results.append({
                        "filename": os.path.basename(s3_path),
                        "subfolder": os.path.dirname(s3_path),
                        "type": "custom"
                    })

            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        return {"ui": {"images": results}, "result": (s3_image_paths,)}