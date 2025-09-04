# app/services/storage_manager.py

import os
import boto3
from botocore.exceptions import ClientError

from dotenv import load_dotenv
load_dotenv()


class S3FileManager:
    def __init__(self):
        self.bucket = os.getenv("AWS_S3_BUCKET_NAME")
        region = os.getenv("AWS_DEFAULT_REGION")
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if not all([self.bucket, region, access_key, secret_key]):
            raise RuntimeError("Variáveis AWS_* não configuradas no .env")

        self.client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

    # -------- Arquivos --------
    def upload_file(self, file_path: str, object_name: str) -> str:
        self.client.upload_file(file_path, self.bucket, object_name)
        return object_name

    def download_file(self, object_name: str, dest_path: str):
        self.client.download_file(self.bucket, object_name, dest_path)

    def delete_file(self, object_name: str):
        self.client.delete_object(Bucket=self.bucket, Key=object_name)

    def generate_presigned_url(self, object_name: str, expiration: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_name},
            ExpiresIn=expiration
        )

    # -------- Pastas (prefixos) --------
    def list_folder(self, prefix: str) -> list[str]:
        """Lista arquivos dentro de um prefixo (pasta lógica)."""
        resp = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        if "Contents" not in resp:
            return []
        return [obj["Key"] for obj in resp["Contents"]]

    def folder_exists(self, prefix: str) -> bool:
        """Checa se existe ao menos um objeto nesse prefixo."""
        resp = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix, MaxKeys=1)
        return "Contents" in resp

    def delete_folder(self, prefix: str):
        """Remove todos os objetos de uma pasta lógica."""
        resp = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        if "Contents" not in resp:
            return
        objects = [{"Key": obj["Key"]} for obj in resp["Contents"]]
        self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": objects})
