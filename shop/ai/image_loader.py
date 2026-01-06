import requests
import tempfile

def download_cloudinary_image(image_url):
    response = requests.get(image_url, stream=True)

    if response.status_code != 200:
        raise Exception("Unable to download image")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    for chunk in response.iter_content(1024):
        temp_file.write(chunk)

    temp_file.close()
    return temp_file.name
