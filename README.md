# VideoSearchRestV2

A REST API service for multimodal video search powered by LanguageBind. Index videos and search using text, images, or audio queries.

## Features

- **Multimodal Search**: Query videos using text, images, or audio
- **Video Indexing**: Extract and store embeddings from video, audio, and visual content
- **Scene Detection**: Automatic scene boundary detection for efficient indexing
- **Multiple Databases**: Organize indexed content across different databases
- **License Management**: Built-in licensing system with usage tracking

## Quick Start

### Prerequisites

- Python 3.8+
- CUDA-capable GPU (recommended)
- PostgreSQL or compatible database

### Installation

```bash
pip install -r requirements.txt
```

### Run the Server

```bash
python app.py -db "postgresql://user:pass@host:port/dbname" -p 5801 -w work_dir -b 8
```

**Arguments:**
- `-db`: Database connection URL (required)
- `-p`: Port number (default: 5801)
- `-w`: Working directory (default: work_dir)
- `-b`: Batch size for indexing (default: 8)

## API Endpoints

### Indexing
- `POST /index-videos` - Index video files
- `POST /remove-video` - Remove indexed video

### Search
- `POST /textsearch` - Search using text queries
- `POST /imagesearch` - Search using image queries
- `POST /audiosearch` - Search using audio queries

### Management
- `GET /status` - Get system status
- `POST /licence-requirement` - Check license status

## Example Usage

### Index a Video
```bash
curl -X POST http://localhost:5801/index-videos \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{
      "filepath": "/path/to/video.mp4",
      "sourceId": "video1",
      "fps": 30,
      "useAudio": true
    }],
    "dbName": "my_database"
  }'
```

### Text Search
```bash
curl -X POST http://localhost:5801/textsearch \
  -H "Content-Type: application/json" \
  -d '{
    "query": "person walking in park",
    "limit": 10,
    "dbName": "*"
  }'
```

## Configuration

Edit `config.py` or set environment variables:
- `STARTDATE`: License start date
- `PASSWORD`: License password
- Scene detection and embedding parameters

## License

Licensed software with usage tracking. Contact for license keys.

## License URL
https://licenseserver-lime.vercel.app

Admin_Secret 26d01a48e2c6b9b955a28c74760eb59f
License_Secret ac507f26d1928db1a1e79ac108995b20d2e11d72ee0c398d24834e9f91429be5
