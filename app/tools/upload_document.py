"""S3 document upload tool with multipart upload support for large files.

Uses boto3 S3 client to upload documents to the ntkey-idp-documents bucket.
Files larger than CHUNK_SIZE (10 MB) use multipart upload; smaller files
use simple put_object.
"""

import os

from strands import tool

from app.config import CHUNK_SIZE, S3_BUCKET_NAME, get_boto_session


@tool
def upload_document_to_s3(file_path: str, file_name: str) -> str:
    """Upload a document to S3 with multipart upload support for large files.

    Uploads the file at the given local path to the S3 bucket configured in
    the application (ntkey-idp-documents). Files larger than 10 MB are uploaded
    using S3 multipart upload for reliability. Smaller files use a simple
    put_object call.

    Args:
        file_path: Absolute path to the local file to upload.
        file_name: The desired file name in S3 (stored under uploads/ prefix).

    Returns:
        The S3 URI of the uploaded file (e.g. s3://ntkey-idp-documents/uploads/report.pdf).
    """
    session = get_boto_session()
    s3_client = session.client("s3")
    s3_key = f"uploads/{file_name}"
    file_size = os.path.getsize(file_path)

    if file_size < CHUNK_SIZE:
        # Small file: use simple put_object
        with open(file_path, "rb") as f:
            s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=f.read())
        return f"s3://{S3_BUCKET_NAME}/{s3_key}"

    # Large file: use multipart upload
    upload_id: str | None = None
    try:
        response = s3_client.create_multipart_upload(Bucket=S3_BUCKET_NAME, Key=s3_key)
        upload_id = response["UploadId"]
        parts: list[dict[str, object]] = []
        part_number = 1

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                part_response = s3_client.upload_part(
                    Bucket=S3_BUCKET_NAME,
                    Key=s3_key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=chunk,
                )
                parts.append({"ETag": part_response["ETag"], "PartNumber": part_number})
                part_number += 1

        s3_client.complete_multipart_upload(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )
        return f"s3://{S3_BUCKET_NAME}/{s3_key}"

    except Exception as exc:
        # Abort multipart upload on any failure to avoid orphaned parts
        if upload_id is not None:
            try:
                s3_client.abort_multipart_upload(
                    Bucket=S3_BUCKET_NAME, Key=s3_key, UploadId=upload_id
                )
            except Exception:
                pass  # Best-effort cleanup
        raise RuntimeError(f"Failed to upload {file_name} to S3: {exc}") from exc
