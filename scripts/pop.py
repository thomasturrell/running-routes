import requests
import zipfile
import os
from io import BytesIO

# URL of the ZIP file
url = "https://www.hills-database.co.uk/hillcsv.zip"

# Download the ZIP file
print("Downloading ZIP file...")
response = requests.get(url)
response.raise_for_status()

# Create a directory to extract files
extract_dir = "hillcsv_data"
os.makedirs(extract_dir, exist_ok=True)

# Extract the ZIP content
print("Extracting files...")
with zipfile.ZipFile(BytesIO(response.content)) as z:
    z.extractall(extract_dir)

# List extracted CSV files
print("Extracted files:")
for file_name in os.listdir(extract_dir):
    if file_name.endswith(".csv"):
        print(f" - {file_name}")
