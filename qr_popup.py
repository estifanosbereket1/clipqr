import os

import qrcode
from dotenv import load_dotenv

load_dotenv()


def generate_qr_for_entry(entry_id: int) -> str:
    base_url = os.getenv("BASE_URL")
    url = f"{base_url}/c/{entry_id}"
    image_path = f"/tmp/clipqr_qr_{entry_id}.png"
    qrcode.make(url).save(image_path)
    return image_path
