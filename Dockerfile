FROM python:3.12

WORKDIR /main_app


RUN apt update && \
    apt install -y git wget ffmpeg libsm6 libxext6 dmidecode sudo 

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu128 && \
    pip install --no-cache-dir -r requirements.txt 

COPY cache_dir /main_app/cache_dir
COPY utils /main_app/utils
COPY embedding_model /main_app/embedding_model

COPY generate_key.pyc .
COPY app.pyc .
COPY config.pyc .
COPY db_utils.pyc .
COPY model.pyc .
COPY setup_db.pyc .


# Create symlink for Faiss
RUN cd /usr/local/lib/python3.12/site-packages/faiss && \
    ln -s swigfaiss.py swigfaiss_avx2.py

WORKDIR /main_app

EXPOSE 5800

ENTRYPOINT ["python", "-W", "ignore", "app.pyc"]
# ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "myenv", "python", "app.pyc"]

CMD ["--working_dir", "/work_dir", "--batch_size", "32", "--port", "5800", "--database_url", "sqlite:///work_dir/video_search.db"]