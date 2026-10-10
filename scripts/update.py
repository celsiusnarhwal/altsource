# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "httpx2>=2.13.1",
#     "pillow>=12.3.0",
# ]
# ///

import argparse
import json
import plistlib
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import httpx2 as httpx
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument("--ipa", required=True)
parser.add_argument("--bundle-id", required=True)
parser.add_argument("--description", default="")
args = parser.parse_args(sys.argv[1:])

altsource_file = Path("altsource.json")
altsource = json.loads(altsource_file.read_text())

itunes_metadata = (
    httpx.get(
        "https://itunes.apple.com/lookup",
        params={"bundleId": args.bundle_id},
    )
    .raise_for_status()
    .json()["results"][0]
)

ZipFile(Path(args.ipa)).extractall()

info_plist = plistlib.loads(next(Path("Payload").glob("*.app/Info.plist")).read_bytes())

app = next(
    app
    for app in altsource["apps"]
    if app["bundleIdentifier"] == info_plist["CFBundleIdentifier"]
)

app.update = {
    "localizedDescription": args.description,
    "iconURL": itunes_metadata["artworkUrl100"],
    "screenshots": {},
}

for device in ["iphone", "ipad"]:
    for screenshot_url in itunes_metadata.get(
        "ipadScreenshotUrls" if device == "ipad" else "screenshotUrls", []
    ):
        screenshot = Image.open(
            BytesIO(httpx.get(screenshot_url).raise_for_status().content)
        )

        app["screenshots"].setdefault(device, []).append(
            {
                "imageURL": screenshot_url,
                "width": screenshot.width,
                "height": screenshot.height,
            }
        )

altsource_file.write_text(json.dumps(altsource, indent=2))
