from typing import List, Optional

from pydantic import BaseModel


class BaseSourceModel(BaseModel):
    name: str
    version: str
    source: str
    embedding_model: str
    vector_store_name: str

    def pipeline_name(self) -> str:
        return self.vector_store_name


class GitHubSource(BaseSourceModel):
    url: str
    path: str
    token: Optional[str] = ""
    branch: Optional[str] = ""


class S3Source(BaseSourceModel):
    access_key_id: str
    secret_access_key: str
    endpoint_url: str
    bucket_name: str
    region: str


class URLsSource(BaseSourceModel):
    urls: List[str]
