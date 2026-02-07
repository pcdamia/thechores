import os
from werkzeug.utils import secure_filename
from PIL import Image
import uuid

# Use /data/uploads in HA (writable); static/uploads for local dev
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, subfolder='', crop_data=None):
    """Save uploaded file and return the relative path
    crop_data: dict with 'x', 'y', 'width', 'height' for cropping
    """
    if not file or not allowed_file(file.filename):
        return None
    
    # Create upload directory structure (UPLOAD_FOLDER may be absolute e.g. /data/uploads)
    upload_path = os.path.join(UPLOAD_FOLDER, subfolder)
    os.makedirs(upload_path, exist_ok=True)
    
    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_path, filename)
    
    # Save file
    file.save(filepath)
    
    # Process image
    try:
        img = Image.open(filepath)
        
        # Apply crop if provided
        if crop_data:
            x = int(crop_data.get('x', 0))
            y = int(crop_data.get('y', 0))
            width = int(crop_data.get('width', img.width))
            height = int(crop_data.get('height', img.height))
            img = img.crop((x, y, x + width, y + height))
        
        # Resize image if it's too large
        if subfolder == 'profiles':
            # Profile images should be square
            if crop_data:
                # Crop has already been applied, ensure it's square
                # If crop resulted in non-square, center crop to square
                size = min(img.width, img.height)
                if img.width != img.height:
                    left = (img.width - size) // 2
                    top = (img.height - size) // 2
                    img = img.crop((left, top, left + size, top + size))
            else:
                # If no crop data, center crop to square
                size = min(img.width, img.height)
                left = (img.width - size) // 2
                top = (img.height - size) // 2
                img = img.crop((left, top, left + size, top + size))
            
            # Resize to 400x400 for profile images (maintains square aspect)
            img = img.resize((400, 400), Image.Resampling.LANCZOS)
        else:
            # Other images max 1200x1200
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        
        img.save(filepath, optimize=True, quality=85)
    except Exception as e:
        print(f"Error processing image: {e}")
    
    # Return path relative to upload root for URL: /static/uploads/<this>
    if subfolder:
        return os.path.join(subfolder, filename).replace('\\', '/')
    return filename

def delete_uploaded_file(filepath):
    """Delete an uploaded file. filepath is e.g. uploads/profiles/xxx.jpg"""
    if filepath:
        rel = filepath.replace('uploads/', '').replace('uploads\\', '')
        full_path = os.path.join(UPLOAD_FOLDER, rel) if os.path.isabs(UPLOAD_FOLDER) else os.path.join('static', filepath)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                print(f"Error deleting file: {e}")
