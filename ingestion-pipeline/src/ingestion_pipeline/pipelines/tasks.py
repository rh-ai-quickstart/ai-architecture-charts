import os
from typing import Optional

from kfp import dsl

BASE_IMAGE = os.environ["INGESTION_PIPELINE_IMAGE"]


@dsl.component(base_image=BASE_IMAGE)
def fetch_from_s3(output_dir: dsl.OutputPath()):
    import os
    import boto3

    # S3 Config
    bucket_name = os.environ.get("BUCKET_NAME")
    minio_endpoint = os.environ.get("ENDPOINT_URL")
    minio_access_key = os.environ.get("ACCESS_KEY_ID")
    minio_secret_key = os.environ.get("SECRET_ACCESS_KEY")

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")

    # Connect to MinIO
    print(f"Connecting to MinIO at {minio_endpoint}")
    s3 = boto3.client(
        "s3",
        endpoint_url=minio_endpoint,
        aws_access_key_id=minio_access_key,
        aws_secret_access_key=minio_secret_key,
        verify=False,
    )

    # List and download objects
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket_name)

    print(f"Downloading files from bucket: {bucket_name}")
    downloaded_files = []
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            file_path = os.path.join(output_dir, os.path.basename(key))
            print(f"Downloading: {key} -> {file_path}")
            s3.download_file(bucket_name, key, file_path)
            downloaded_files.append(file_path)

    print(f"Downloaded {len(downloaded_files)} files to {output_dir}")

    if not downloaded_files:
        raise Exception(
            f"No files found in bucket: {bucket_name}. Please check your bucket configuration."
        )

    print(f"Contents of output directory: {os.listdir(output_dir)}")


@dsl.component(base_image=BASE_IMAGE)
def fetch_from_urls(output_dir: dsl.OutputPath()):
    print(f"Storing documents will fetch from URLS env var")


@dsl.component(base_image=BASE_IMAGE)
def fetch_from_github(output_dir: dsl.OutputPath()):
    import os
    import shutil
    import tempfile
    import git

    os.makedirs(output_dir, exist_ok=True)
    token = os.getenv("GIT_TOKEN")
    url = os.getenv("GIT_URL")
    counter = 0
    if token:
        if url.startswith("https://"):
            url = url.replace("https://", f"https://{token}@")
        else:
            raise ValueError("Only HTTPS URLs support token authentication")
    with tempfile.TemporaryDirectory() as tmp_dir:
        kwargs = {"depth": 1, "single_branch": True}
        if branch := os.getenv("GIT_BRANCH"):
            kwargs["branch"] = branch
        git.Repo.clone_from(url, tmp_dir, **kwargs)
        src_dir = os.path.join(tmp_dir, os.getenv("GIT_PATH"))
        if os.path.isdir(src_dir):
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Create relative path from src_dir to maintain directory structure
                    rel_path = os.path.relpath(file_path, src_dir)
                    dest_path = os.path.join(output_dir, rel_path)

                    # Create destination directory if it doesn't exist
                    dest_dir = os.path.dirname(dest_path)
                    if (
                        dest_dir
                    ):  # Only create if there's actually a directory to create
                        os.makedirs(dest_dir, exist_ok=True)

                    print(f"Copying {rel_path} to {dest_path}")
                    shutil.copy2(file_path, dest_path)
                    counter += 1
        else:
            raise RuntimeError(f"Directory {src_dir} not found in the repo.")

    print(f"Total files copied: {counter}")


@dsl.component(base_image=BASE_IMAGE)
def store_documents(llamastack_base_url: str, input_dir: dsl.InputPath(), auth_user: str):
    import os
    import asyncio
    from pathlib import Path

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions

    # Import docling libraries
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
    from docling_core.types.doc.labels import DocItemLabel
    from llama_stack_client import AsyncLlamaStackClient
    from llama_stack_client.types import Document as LlamaStackDocument

    os.environ["EASYOCR_MODULE_PATH"] = "/tmp/.EasyOCR"

    # Configuring the vector store
    embedding_model = os.getenv("EMBEDDING_MODEL")
    vector_store_name = os.getenv("VECTOR_STORE_NAME")

    # Setup docling components
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True
    converter = DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.MD,
            InputFormat.DOCX,
            InputFormat.ASCIIDOC,
            InputFormat.JSON_DOCLING,
            InputFormat.HTML,
        ],  # TODO: add YAML
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        },
    )
    chunker = HybridChunker()
    llama_documents = []
    i = 0
    # Process each file with docling (chunking)
    input_files = []
    if os.getenv("URLS"):
        import ast

        input_files = ast.literal_eval(os.getenv("URLS", "[]"))
    else:
        input_files = [str(p) for p in Path(input_dir).iterdir() if p.is_file()]
    if not input_files:
        raise RuntimeError("No input files found")
    print(f"Input files: {input_files}")
    for file_path in input_files:
        print(f"Processing {file_path} with docling...")
        try:
            docling_doc = converter.convert(source=file_path).document
            chunks = chunker.chunk(docling_doc)
            chunk_count = 0

            for chunk in chunks:
                if any(
                    c.label
                    in [
                        DocItemLabel.TEXT,
                        DocItemLabel.PARAGRAPH,
                        DocItemLabel.TABLE,
                        DocItemLabel.PAGE_HEADER,
                        DocItemLabel.PAGE_FOOTER,
                        DocItemLabel.TITLE,
                        DocItemLabel.PICTURE,
                        DocItemLabel.CHART,
                        DocItemLabel.DOCUMENT_INDEX,
                        DocItemLabel.SECTION_HEADER,
                    ]
                    for c in chunk.meta.doc_items
                ):
                    i += 1
                    chunk_count += 1
                    llama_documents.append(
                        LlamaStackDocument(
                            document_id=f"doc-{i}",
                            content=chunk.text,
                            mime_type="text/plain",
                            metadata={"source": os.path.basename(file_path)},
                        )
                    )
            print(f"Created {chunk_count} chunks from {file_path}")

        except Exception as e:
            error_message = str(e)
            print(f"Error processing {file_path}: {error_message}")

    total_chunks = len(llama_documents)
    print(f"Total valid chunks prepared: {total_chunks}")

    # Add error handling for zero chunks
    if total_chunks == 0:
        raise Exception(
            "No valid chunks were created. Check document processing errors above."
        )

    # Step 3: Register vector database and store chunks with embeddings
    headers = {}
    if auth_user:
        headers={"X-Forwarded-User": auth_user}
        file_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        try:
            with open(file_path, "r") as file:
                token = file.read()
                headers["Authorization"]=f"Bearer {token}"
        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")
        except Exception as e:
            print(f"An error occurred: {e}")

    client = AsyncLlamaStackClient(
        base_url=llamastack_base_url,
        default_headers=headers,
    )
    print("Creating vector store")
    try:
        vector_store = asyncio.run(client.vector_stores.create(
            name=vector_store_name,
            embedding_model=embedding_model,
            embedding_dimension=384,
            provider_id="pgvector",
        ))
        vector_store_id = vector_store.id
        print(f"Vector store created successfully with ID: {vector_store_id}")
    except Exception as e:
        error_message = str(e)
        print(f"Failed to create vector store: {error_message}")
        raise Exception(f"Vector store creation failed: {error_message}")

    try:
        print(f"Processing {total_chunks} chunks for vector store insertion")
        import tempfile
        import json

        # Create temporary files for each document chunk and upload them
        uploaded_files = []
        for i, doc in enumerate(llama_documents):
            # Create a temporary file for each chunk
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                # Write the document content to the file
                temp_file.write(doc.content)
                temp_file_path = temp_file.name

            try:
                # Upload the file to the Files API
                with open(temp_file_path, 'rb') as file_content:
                    file_response = asyncio.run(client.files.create(
                        file=file_content,
                        purpose="assistants"
                    ))

                # Attach the file to the vector store
                file_attach_response = asyncio.run(client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=file_response.id,
                    attributes=doc.metadata,
                ))

                uploaded_files.append({
                    'file_id': file_response.id,
                    'attach_response': file_attach_response,
                    'source': doc.metadata.get('source', f'chunk-{i}')
                })

                print(f"Uploaded and attached file {i+1}/{total_chunks}: {doc.metadata.get('source', f'chunk-{i}')}")

            finally:
                # Clean up temporary file
                import os
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

        # Wait for all files to be processed
        print("Waiting for all files to be processed...")
        import time
        for file_info in uploaded_files:
            while True:
                status_response = asyncio.run(client.vector_stores.files.retrieve(
                    vector_store_id=vector_store_id,
                    file_id=file_info['file_id']
                ))

                if status_response.status == "completed":
                    print(f"File {file_info['source']} processed successfully")
                    break
                elif status_response.status == "failed":
                    print(f"Warning: File {file_info['source']} failed to process: {status_response.last_error}")
                    break
                elif status_response.status == "in_progress":
                    print(f"File {file_info['source']} still processing...")
                    time.sleep(1)
                else:
                    print(f"Unknown status for file {file_info['source']}: {status_response.status}")
                    break

        print(f"Successfully uploaded and processed {len(uploaded_files)} files to vector store")

    except Exception as e:
        print("Vector store insertion failed:", e)
        raise Exception(f"Failed to insert documents into vector store: {e}")


@dsl.component(base_image=BASE_IMAGE)
def generate_provenance(input_dir: dsl.InputPath()):
    import base64
    import datetime
    import gzip
    import hashlib
    import json
    import llama_stack_client
    import io
    import os
    import requests
    import subprocess

    from kubernetes import client, config, stream
    from pathlib import Path

    # Connect to the cluster
    config.load_incluster_config()

    def get_predicate_skeleton() -> dict:
        return {
            "buildType": "kubeflow.org/v1/Notebook",
            "buildDefinition": {
                "buildType": "kubeflow.org/v1/Notebook",
                "externalParameters": {},
                "internalParameters": {
                    "environment": {
                        "embedding_model": os.getenv('EMBEDDING_MODEL'),
                        "llama_stack_client": f"{llama_stack_client.__version__}",
                    },
                },
                "resolvedDependencies": [],
            },
            "runDetails": {
                "metadata": {
                    "finishedOn": f"{datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}",
                },
            },
        }

    def get_db_sha() -> str:
        secret_name="pgvector" # Needs to be hardcoded for the moment

        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            namespace = f.read().strip()
        secret = client.CoreV1Api().read_namespaced_secret(secret_name, namespace)
        container = base64.b64decode(secret.data["host"]).decode("utf-8")
        db_name=base64.b64decode(secret.data["dbname"]).decode("utf-8")
        db_username = base64.b64decode(secret.data["user"]).decode("utf-8")
        pod = f"{container}-0"

        command = [
            "/bin/bash",
            "-c",
            f"pg_dump -U {db_username} -d {db_name} | grep -v -E '^\\\\(un)?restrict ' | sha512sum -",
        ]
        # Exec into the container
        resp = stream.stream(
            client.CoreV1Api().connect_get_namespaced_pod_exec,
            namespace=namespace,
            name=pod,
            container=container,
            command=command,
            stderr=True,
            stdin=True,
            stdout=True,
            tty=True,
        )
        sha = resp.split()[0]
        return sha

    def get_sources_sha():
        chunk_size = 2**20
        files=[p for p in Path(input_dir).iterdir() if p.is_file()]
        for file in files:
            shasum = hashlib.sha512()
            with file.open("rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    shasum.update(chunk)
            yield (
                file.as_uri(),
                shasum.hexdigest(),
            )

    def get_cosign() -> str:
        # Get URL from which to download the binary
        route = client.CustomObjectsApi().list_namespaced_custom_object(
            group="route.openshift.io",
            version="v1",
            namespace="trusted-artifact-signer",
            plural="routes",
            label_selector="app.kubernetes.io/component=client-server"
        )
        host = route["items"][0]["spec"]["host"]
        url = f"https://{host}/clients/linux/cosign-amd64.gz"

        # Download the binary archive
        response = requests.get(url)
        response.raise_for_status()

        # Decompress the archive
        with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
            decompressed = f.read()

        # Write the binary to disk and make it executable
        bin_path = "/tmp/cosign"
        with open(bin_path, "wb") as f:
            f.write(decompressed)
        os.chmod(bin_path, 0o755)


        # Get TUF URL
        route = client.CustomObjectsApi().list_namespaced_custom_object(
            group="route.openshift.io",
            version="v1",
            namespace="trusted-artifact-signer",
            plural="routes",
            label_selector="app.kubernetes.io/component=tuf"
        )
        tuf_url=f"https://{route["items"][0]["spec"]["host"]}"
        root_path=f"{tuf_url}/root.json"

        # Workaroud for broken TAS
        tuf_url="https://tuf-repo-cdn.sigstage.dev"
        response = requests.get("https://raw.githubusercontent.com/sigstore/root-signing-staging/main/metadata/root_history/1.root.json")
        response.raise_for_status()
        root_path="/tmp/tuf-root.json"
        with open(root_path, "wb") as f:
            f.write(response.content)

        run_cosign([
            bin_path,
            "initialize",
            f"--mirror={tuf_url}",
            f"--root={root_path}",
        ])

        return bin_path

    def get_rekor() -> str:
        route = client.CustomObjectsApi().list_namespaced_custom_object(
            group="route.openshift.io",
            version="v1",
            namespace="trusted-artifact-signer",
            plural="routes",
            label_selector="app.kubernetes.io/component=rekor-server"
        )
        host = route["items"][0]["spec"]["host"]
        return f"https://{host}"

    def get_signing_key() -> str:
        secret = client.CoreV1Api().read_namespaced_secret("signing-secrets", "openshift-pipelines")
        key = base64.b64decode(secret.data["cosign.key"]).decode("utf-8")
        password = base64.b64decode(secret.data["cosign.password"]).decode("utf-8")
        return (key, password)

    def run_cosign(command: list):
        cosign_key, cosign_password = get_signing_key()

        result = subprocess.run(
            command,
            capture_output=True,
            env={
                "COSIGN_KEY": cosign_key,
                "COSIGN_PASSWORD": cosign_password,
                "HOME": "/tmp",
            },
            text=True
        )
        if result.returncode != 0:
            print("Output:")
            print(result.stdout)
            print("Error:")
            print(result.stderr)
            raise RuntimeError("cosign command failed")

        return result.stdout

    def cosign(predicate: str, blob: str) -> str:
        bin_path = get_cosign()
        rekor_url = get_rekor()
        # Workaround for TAS storage issue
        rekor_url = "https://rekor.sigstage.dev"

        predicate_path = "/tmp/predicate.json"
        with open(predicate_path, "w") as f:
            f.write(predicate)

        print()
        print("Attesting blob")
        blob_path = "/tmp/db.sha512sum"
        blob_data=f"att:{blob}"
        with open(blob_path, "w") as f:
            f.write(blob_data)
        run_cosign([
            bin_path,
            "attest-blob",
            blob_path,
            "--key=env://COSIGN_KEY",
            "--predicate="+predicate_path,
            "--rekor-entry-type=intoto",
            "--rekor-url="+rekor_url,
            "--type=slsaprovenance1",
            "-y",
        ])
        shasum = hashlib.sha256()
        shasum.update(blob_data.encode())
        att_sha = shasum.hexdigest()

        print()
        print("Signing blob")
        blob_path = "/tmp/db.sha512sum"
        blob_data=f"sig:{blob}"
        with open(blob_path, "w") as f:
            f.write(blob_data)
        run_cosign([
            bin_path,
            "sign-blob",
            blob_path,
            "--key=env://COSIGN_KEY",
            "--rekor-url="+rekor_url,
            "-y",
        ])
        shasum = hashlib.sha256()
        shasum.update(blob_data.encode())
        sig_sha = shasum.hexdigest()

        return (att_sha, sig_sha)

    predicate = get_predicate_skeleton()

    # Add subject
    db_sha = get_db_sha()

    # Add sources
    for source, sha in get_sources_sha():
        dependency = {
            "uri": source,
            "digest": {
                "sha512": sha,
            },
        }
        predicate["buildDefinition"]["resolvedDependencies"].append(dependency)

    # Sign
    predicate_str = json.dumps(predicate, indent=2)
    print("\n\n")
    print(f"DB sha: '{db_sha}'")
    print("Predicate:")
    print(predicate_str)
    print("\n\n")
    print()

    att_sha, sig_sha = cosign(predicate_str, db_sha)
    print("\n\n")
    print(f"Attestation Hash: 'sha256:{att_sha}'")
    print(f"Signing Hash: 'sha256:{sig_sha}'")

    print("\n\n")
