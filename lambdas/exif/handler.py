import json
from PIL import Image
import io
import boto3
from pathlib import Path

def download_from_s3(bucket, key):
    s3 = boto3.client('s3')
    buffer = io.BytesIO()
    s3.download_fileobj(bucket, key, buffer)
    buffer.seek(0)
    return Image.open(buffer)

def upload_to_s3(bucket, key, data, content_type='image/jpeg'):
    s3 = boto3.client('s3')
    if isinstance(data, Image.Image):
        buffer = io.BytesIO()
        data.save(buffer, format='JPEG')
        buffer.seek(0)
        s3.upload_fileobj(buffer, bucket, key)
    else:
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)

def exif_handler(event, context):
    """
    EXIF Lambda - Process all images in the event
    """
    print("EXIF Lambda triggered")
    print(f"Event received with {len(event.get('Records', []))} SNS records")

    processed_count = 0
    failed_count = 0

    # iterate over all SNS records
    for sns_record in event.get('Records', []):
        try:
            # extract and parse SNS message
            sns_message = json.loads(sns_record['Sns']['Message'])

            # iterate over all S3 records in the SNS message
            for s3_event in sns_message.get('Records', []):
                try:
                    s3_record = s3_event['s3']
                    bucket_name = s3_record['bucket']['name']
                    object_key = s3_record['object']['key']

                    print(f"Processing: s3://{bucket_name}/{object_key}")

                    ######
                    #
                    #  TODO: add exif lambda code here
                    #
                    ######
                    # Download image from S3
                    image = download_from_s3(bucket_name, object_key)

                    # Extract EXIF metadata
                    exif_data = image.getexif()
                    metadata = {}

                    def safe_convert(value):
                        """Convert EXIF values to JSON-safe types."""
                        try:
                            # Handle Pillow IFDRational / TiffIFDRational
                            if value.__class__.__name__ in ("IFDRational", "TiffIFDRational"):
                                return float(value)
                            # Handle fraction-like objects
                            if hasattr(value, "numerator") and hasattr(value, "denominator"):
                                return float(value.numerator) / float(value.denominator)
                            # Handle bytes
                            if isinstance(value, bytes):
                                return value.decode(errors="ignore")
                            # Handle sequences
                            if isinstance(value, (list, tuple)):
                                return [safe_convert(v) for v in value]
                            # Basic JSON types
                            if isinstance(value, (str, int, float, bool)) or value is None:
                                return value
                            # Fallback: string conversion
                            return str(value)
                        except Exception as e:
                            return f"unserializable ({str(e)})"

                    for tag, value in exif_data.items():
                        tag_name = str(tag)
                        metadata[tag_name] = safe_convert(value)

                    if not metadata:
                        metadata = {"info": "No EXIF metadata found"}

                    json_data = json.dumps(metadata, indent=2, ensure_ascii=False).encode("utf-8")

                    filename = Path(object_key).stem
                    output_key = f"processed/exif/{filename}.json"
                    upload_to_s3(bucket_name, output_key, json_data, content_type="application/json")
                    print(f"Uploaded EXIF data to s3://{bucket_name}/{output_key}")
                    processed_count += 1


                except Exception as e:
                    failed_count += 1
                    error_msg = f"Failed to process {object_key}: {str(e)}"
                    print(error_msg)

        except Exception as e:
            print(f"Failed to process SNS record: {str(e)}")
            failed_count += 1

    summary = {
        'statusCode': 200 if failed_count == 0 else 207,  # @note: 207 = multi-status
        'processed': processed_count,
        'failed': failed_count,
    }

    print(f"Processing complete: {processed_count} succeeded, {failed_count} failed")
    return summary