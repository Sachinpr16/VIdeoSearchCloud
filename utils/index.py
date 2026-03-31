from scenedetect import open_video, SceneManager
from scenedetect import detectors
from scenedetect.frame_timecode import FrameTimecode
from decord import cpu, VideoReader
from decord._ffi.base import DECORDError
from werkzeug.utils import secure_filename
import tempfile
import shutil
import math
import copy
import whisper

from utils.base import *
from model import  get_video_embedding, get_text_embedding_batch, get_languagebind_model
from utils.licence import check_licence_validation, set_recent_date, get_recent_date, update_usage_hours
from config import get_config


# Get the global configuration instance
config = get_config()

prevProcessedVideo = None
vidReader = None


def find_scenes_from_images(image_folder: str, image_pattern: str, fps: float, threshold: float = 27.0):
    image_sequence_path = os.path.join(image_folder, image_pattern)

    video_stream = None 
    try:
        print(f"Attempting to open image sequence: {image_sequence_path} with FPS: {fps}")
        video_stream = open_video(path=image_sequence_path, framerate=fps)
        
        if video_stream.frame_size[0] == 0 or video_stream.frame_size[1] == 0:
            # raise RuntimeError(f"Could not open or read the initial images in the sequence: {image_sequence_path}. "
            #                    "Please check the path, pattern, and ensure images exist and are readable. "
            #                    "Also, ensure image numbering starts as expected by the pattern (e.g., 0 or 1 for %d.jpg).")
            print((f"Could not open or read the initial images in the sequence: {image_sequence_path}. "
                               "Please check the path, pattern, and ensure images exist and are readable. "
                               "Also, ensure image numbering starts as expected by the pattern (e.g., 0 or 1 for %d.jpg)."))

        print(f"Successfully opened image sequence. Detected frame size: {video_stream.frame_size}, Duration: {video_stream.duration}")

    except Exception as e:
        print(f"Error opening image sequence: {e}")
        print("Please ensure that:")
        print(f"1. The image folder '{image_folder}' exists and contains images.")
        print(f"2. The image_pattern '{image_pattern}' is correct (e.g., '%d.jpg' for 0.jpg, 1.jpg...).")
        print("3. OpenCV (used by PySceneDetect) can read the image format and sequence.")
        print("4. Image numbering starts from 0 or 1 if using a simple '%d.jpg' pattern.")
        return None

    scene_manager = SceneManager()


    scene_manager.add_detector(detectors.ContentDetector(threshold=threshold))

    try:

        print(f"\nDetecting scenes in {image_sequence_path} at {fps} FPS using threshold {threshold}...")
        
        scene_manager.detect_scenes(video=video_stream, show_progress=False)
        scene_list_tc = scene_manager.get_scene_list()


        if not scene_list_tc:
            # Check if any frames were processed
            if video_stream.frame_number == 0 and video_stream.duration.get_frames() > 0 :
                 print("Warning: No frames seem to have been processed from the image sequence, though duration was reported.")
                 print("This might indicate an issue with OpenCV reading past the first few frames or an incorrect sequence pattern/numbering.")
            elif video_stream.frame_number == 0 and video_stream.duration.get_frames() == 0:
                 print("Warning: The image sequence appears to be empty or could not be read by OpenCV.")
            return []


        return scene_list_tc

    except Exception as e:
        print(f"Error during scene detection: {e}")
        return None


def detect_scenes(video_path, source_id, threshold, is_video=True, video_fps=30, manual_scene_frames=None):
    try:
        folder_name = source_id
        if not is_video and manual_scene_frames is not None:
            if folder_name in manual_scene_frames and manual_scene_frames[folder_name]:  
                frame_numbers = manual_scene_frames[folder_name]
                
                if not frame_numbers or not isinstance(frame_numbers, list):
                    print(f"Invalid frame numbers for {folder_name}, falling back to automatic detection")
                else:
                    scene_list = []
                    image_files = [f for f in os.listdir(video_path) if f.lower().endswith('.jpg')]
                    total_frames = len(image_files) - 1
                    
                    if not total_frames:
                        # raise ValueError(f"No JPG files found in {video_path}")
                        print(f"No JPG files found in {video_path}")
                    
                    frame_numbers.sort()
                    frame_numbers = [int(i) for i in frame_numbers]
                    
                    start_frame = 0
                    
                    for frame in frame_numbers:
                        if frame >= total_frames:
                            continue
                        if frame > start_frame and frame < total_frames:
                            start_timecode = FrameTimecode(start_frame, video_fps)
                            end_timecode = FrameTimecode(frame, video_fps)
                            scene_list.append((start_timecode, end_timecode))
                            start_frame = frame
                    
                    if start_frame < total_frames:
                        start_timecode = FrameTimecode(start_frame, video_fps)
                        end_timecode = FrameTimecode(total_frames, video_fps)
                        scene_list.append((start_timecode, end_timecode))
                    
                    print(f"Created {len(scene_list)} scenes from manual frame list for {folder_name}")
                    return scene_list, video_fps
        
        if is_video:
            video = open_video(video_path)
            frame_rate = video.frame_rate
            total_frames = int(frame_rate * video.duration.get_seconds())
            scene_manager = SceneManager()
            scene_manager.add_detector(detectors.ContentDetector(threshold=threshold))
            
            scene_manager.detect_scenes(video)
            scene_list = scene_manager.get_scene_list()
            

            if not scene_list or len(scene_list) == 0:
                scene_list = []
                num_scenes = math.ceil(total_frames / (frame_rate*6))
                frame_numbers = np.linspace(0, total_frames, num_scenes)
                frame_numbers.sort()
                start_frame = 0
                
                for frame in frame_numbers:

                    if frame > start_frame and frame < total_frames:
                        start_timecode = FrameTimecode(int(start_frame), frame_rate)
                        end_timecode = FrameTimecode(int(frame), frame_rate)
                        scene_list.append((start_timecode, end_timecode))
                        start_frame = frame

                if start_frame < total_frames:
                    start_timecode = FrameTimecode(int(start_frame), frame_rate)
                    end_timecode = FrameTimecode(int(total_frames), frame_rate)
                    scene_list.append((start_timecode, end_timecode))
                
                
            return scene_list, frame_rate
        else:
            scene_list = find_scenes_from_images(video_path, "%d.jpg", video_fps, threshold)
            if not scene_list or len(scene_list) == 0:
                scene_list = []
                total_frames = len(os.listdir(video_path))
                num_scenes = math.ceil(total_frames / (video_fps*6))
                frame_numbers = np.linspace(0, total_frames, num_scenes)
                frame_numbers.sort()
                start_frame = 0
                
                for frame in frame_numbers:
                    if frame > start_frame and frame < total_frames:
                        start_timecode = FrameTimecode(int(start_frame), video_fps)
                        end_timecode = FrameTimecode(int(frame), video_fps)
                        scene_list.append((start_timecode, end_timecode))
                        start_frame = frame
                
                if start_frame < total_frames:
                    start_timecode = FrameTimecode(int(start_frame), video_fps)
                    end_timecode = FrameTimecode(int(total_frames), video_fps)
                    scene_list.append((start_timecode, end_timecode))
            return scene_list, video_fps
            
    except Exception as e:
        print(f"Error detecting scenes in {video_path}: {e}")
        import traceback
        traceback.print_exc()
        return [], 0

def sample_frames(video_path, source_id, start_sec, end_sec, num_frames, fps, is_video=True):
    global prevProcessedVideo, vidReader
    if is_video and prevProcessedVideo != source_id:
        # vidReader = VideoReader(video_path, ctx=cpu(0), num_threads=1)
        vidReader = VideoReader(video_path, ctx=cpu(0))
        prevProcessedVideo = source_id 
    
    duration_sec = end_sec - start_sec
    if duration_sec <= 0:
        return []

    if is_video:
        if not vidReader:
            print(f"Error loading video")
            return []

        total_frames = len(vidReader)
        if total_frames < 8:
            return []
        video_fps = vidReader.get_avg_fps()
        if video_fps <= 0:
            video_fps = fps

        start_frame = int(start_sec * video_fps)
        end_frame = min(int(end_sec * video_fps), total_frames - 1)
        
        if end_frame <= start_frame:
            return []
        if end_frame >= total_frames:
            return []
        frame_indices = np.linspace(start_frame, end_frame, num=num_frames, dtype=int)
        
        frames = vidReader.get_batch(frame_indices).asnumpy()
        return frames
    else:
        if not os.path.isdir(video_path):
            print(f"Error: {video_path} is not a directory")
            return []
            
        image_files = [f for f in os.listdir(video_path) if f.lower().endswith('.jpg')]
        image_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
        
        if not image_files:
            print(f"Error: No JPG files found in {video_path}")
            return []
            
        start_frame = int(start_sec * fps)
        end_frame = min(int(end_sec * fps), len(image_files) - 1)
        
        if end_frame <= start_frame:
            return []
            
        frame_indices = np.linspace(start_frame, end_frame, num=num_frames, dtype=int)
        
        frames = []
        for idx in frame_indices:
            idx = int(idx)
            if idx >= len(image_files):
                continue
                
            img_path = os.path.join(video_path, image_files[idx])
            frame = cv2.imread(img_path)
            if frame is None:
                continue
                
            frames.append(frame)
            
        return frames

def preprocess_frames_for_batch(frames):
    if not len(frames):
        return None

    image_size = 224 
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    )
    transform_pipeline = transforms.Compose(
        [
            transforms.Resize(image_size), 
            transforms.CenterCrop(image_size), 
            transforms.ToTensor(), 
            normalize, 
        ]
    )

    transformed_frames = []
    try:
        for frame_bgr in frames:
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            transformed_tensor = transform_pipeline(pil_image) # Output: [C, H, W]
            transformed_frames.append(transformed_tensor)

        if not transformed_frames:
            print("Error: No frames were transformed successfully.")
            return None

        clip_tensor = torch.stack(transformed_frames, dim=0)

        return clip_tensor

    except Exception as e:
        print(f"Error during frame preprocessing: {e}")
        import traceback
        traceback.print_exc()
        return None

def process_embedding_batch_faiss(clip_tensor_batch, clip_metadata_batch, model, device, index, db_name):
    if not clip_tensor_batch:
        return

    try:
        clip_tensor_batch = torch.cat(clip_tensor_batch, dim=0)

        video_embedding = get_video_embedding(clip_tensor_batch, model, device, config.FRAMES_PER_CLIP_FOR_EMBEDDING)
        
        embeddings_np = video_embedding.cpu().numpy()
        current_idx = index.ntotal

        faiss.normalize_L2(embeddings_np)
        ids = np.arange(current_idx, current_idx + len(embeddings_np), dtype='int64')
        index.add_with_ids(embeddings_np, ids)
        db_manager = get_db_manager()
        for i, metadata in enumerate(clip_metadata_batch):
            metadata['faiss_id'] = current_idx + i
        # Save metadata batch to PostgreSQL
        db_manager.insert_metadata_batch(clip_metadata_batch, db_name)

    except Exception as e:
        print(f"Error processing batch: {e}")

def index_audio_and_text(video_path, source_id, is_video, db_name, video_fps=30):
    # Create debug directory structure
    debug_dir = os.path.join(config.OUTPUT_DIR, "..", "debug")
    os.makedirs(debug_dir, exist_ok=True)
    video_name = secure_filename(os.path.splitext(os.path.basename(video_path))[0])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, tokenizer, _ = get_languagebind_model(device)

    def extract_audio_chunks(video_path, chunk_duration=10, is_video=True):
        """
        Extracts audio from a video or image sequence and splits it into chunks of chunk_duration seconds.
        Returns a list of file paths to the audio chunks and total duration.
        """
        audio_chunks = []
        temp_dir = tempfile.mkdtemp()
        try:
            # Step 1: Extract audio to a temporary file
            audio_file = os.path.join(temp_dir, "audio.wav")
            if is_video:
                # Extract audio from video file
                cmd = [
                    "ffmpeg", "-y", "-i", video_path,
                    "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_file
                ]
            else:
                # For image sequence, try to find a matching audio file in the same folder
                # (Assume audio.wav or audio.mp3 exists in the folder)
                possible_audio = None
                for ext in ["wav", "mp3", "aac", "m4a"]:
                    candidate = os.path.join(video_path, f"audio.{ext}")
                    if os.path.exists(candidate):
                        possible_audio = candidate
                        break
                if possible_audio:
                    shutil.copy(possible_audio, audio_file)
                else:
                    # No audio found for image sequence
                    return [], 0
                cmd = None

            if is_video and cmd:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            if not os.path.exists(audio_file):
                return [], 0

            # Step 2: Get audio duration
            probe_cmd = [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of",
                "default=noprint_wrappers=1:nokey=1", audio_file
            ]
            result = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            duration_str = result.stdout.decode().strip()
            if not duration_str:
                return [], 0
            duration = float(duration_str)
            num_chunks = math.ceil(duration / chunk_duration)

            # Step 3: Split audio into chunks
            for i in range(num_chunks):
                start = i * chunk_duration
                out_chunk = os.path.join(temp_dir, f"chunk_{i:04d}.wav")
                split_cmd = [
                    "ffmpeg", "-y", "-i", audio_file,
                    "-ss", str(start), "-t", str(chunk_duration),
                    "-acodec", "copy", out_chunk
                ]
                subprocess.run(split_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(out_chunk):
                    audio_chunks.append(out_chunk)

            return audio_chunks, duration
        except Exception as e:
            print(f"Error extracting audio chunks: {e}")
            return [], 0
        # Note: temp_dir will be cleaned up by the caller if needed
    # Example usage inside index_audio_and_text:
    # Get total duration of the media
    chunk_duration = 30
    # total_duration = get_media_duration(video_path, is_video)
    audio_chunks, total_duration = extract_audio_chunks(video_path, chunk_duration, is_video=is_video)
    print(f"Extracted {len(audio_chunks)} audio chunks from {video_path} (total duration: {total_duration:.2f}s)")
    AUDIO_BATCH_SIZE = config.BATCH_SIZE * 4  # You can adjust this as needed

    index_files = get_index_files(db_name)
    embedding_dim = 768

    # Get database manager for metadata storage
    db_manager = get_db_manager()

    text_model = whisper.load_model("turbo", download_root="cache_dir/whisper")
    text_index = load_index(index_files['text'])
    # print(f"Loaded text index with {text_index.ntotal} entries")
    if text_index is None:
        text_index = faiss.IndexIDMap(faiss.IndexFlatIP(embedding_dim))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Process text chunks
    duration = 0
    text_clip_tensor_batch = []
    text_clip_metadata_batch = []
    text_buffer = ""
    buffer_start_chunk_index = 0
    buffer_start_time = 0
    aud_trans_debug = []
    duration_in_hours = chunk_duration / 3600.0
    config.indexing_status["total_scenes"] += len(audio_chunks)
    config.indexing_status["overall_total_scenes"] += len(audio_chunks)

    max_chunk_indexed = db_manager.get_max_chunk_indexed(source_id, db_name)

    for i, audio_chunk_path in enumerate(audio_chunks):
        # Check if chunk already exists in database
        
        if i <= max_chunk_indexed:
            # print(f"Text chunk {i} for source_id {source_id} already indexed, skipping...")
            config.indexing_status["scenes_processed"] += 1
            continue
        
        # Get audio embedding tensor
        audio_bytes = open(audio_chunk_path, 'rb').read()
        if not audio_bytes:
            print(f"Skipping empty audio chunk: {audio_chunk_path}")
            continue
        text = text_model.transcribe(audio_chunk_path, word_timestamps=True)
        new_text =  text['text'] if isinstance(text, dict) and 'text' in text else text
        
        # total_sentences = text_buffer + " " + new_text
        # sentences = nltk.sent_tokenize(total_sentences)
        sentences = [seg["text"] for seg in text["segments"]]
        time_stamps = [(seg["start"], seg["end"]) for seg in text["segments"]]
        no_speech_probs = [seg["no_speech_prob"] for seg in text["segments"]]
        
        new_sentences = copy.deepcopy(sentences)
        # new_sentences = nltk.sent_tokenize(new_text)
        # new_sentences = [s.strip() for s in new_sentences if s.strip()]
        if not text_buffer:
            buffer_start_chunk_index = i
            buffer_start_time = i * chunk_duration + time_stamps[0][0] if sentences else 0
        
        if sentences:
            sentences[0] = text_buffer + sentences[0]
        uses_buffer = []
        sentences_to_process = sentences
        if sentences and i < len(audio_chunks) - 1:
            # Not the last chunk, so hold back the last sentence fragment
            if sentences[-1].endswith('?') or sentences[-1].endswith('!') or (sentences[-1].endswith('.') and not new_text.endswith('...')):
                sentences_to_process = sentences
                text_buffer = ""
            else:
                sentences_to_process = sentences[:-1]
                text_buffer = sentences[-1]
        else:
            # Last chunk, process everything and clear the buffer
            text_buffer = ""
            buffer_start_chunk_index = i
            buffer_start_time = i * chunk_duration + time_stamps[0][0] if sentences else 0
        for each_sent in sentences_to_process:
            if each_sent not in new_sentences:
                uses_buffer.append(True)
            else:
                uses_buffer.append(False)

        if not sentences:
            # print(f"Skipping chunk {i} as it has no sentences.")
            # current_hours = OFFLINE_LICENSE_LIMIT_HOURS - duration_in_hours
            # OFFLINE_LICENSE_LIMIT_HOURS = max(0.0, current_hours)
            # update_usage_hours(OFFLINE_LICENSE_LIMIT_HOURS)
            config.indexing_status["scenes_processed"] += 1
            continue
                
        if len(sentences) <= 1 and i < len(audio_chunks) - 1 : 
            if new_text.endswith('...'):
                # print(f"Skipping chunk {i} as it has only one sentence and ending with ... , indicating incomplete text.")
                duration += time_stamps[-1][1] - time_stamps[-1][0] 
                # current_hours = OFFLINE_LICENSE_LIMIT_HOURS - duration_in_hours
                # OFFLINE_LICENSE_LIMIT_HOURS = max(0.0, current_hours)
                # update_usage_hours(OFFLINE_LICENSE_LIMIT_HOURS)
                config.indexing_status["scenes_processed"] += 1
                continue
            if not (new_text.endswith('.') or new_text.endswith('!') or new_text.endswith('?')):
                # print(f"Skipping chunk {i} as it has only one sentence and not ending with .?! , indicating incomplete text.")
                duration += time_stamps[-1][1] - time_stamps[-1][0] 
                # current_hours = OFFLINE_LICENSE_LIMIT_HOURS - duration_in_hours
                # OFFLINE_LICENSE_LIMIT_HOURS = max(0.0, current_hours)
                # update_usage_hours(OFFLINE_LICENSE_LIMIT_HOURS)
                config.indexing_status["scenes_processed"] += 1
                continue    

        for sent_num, sent in enumerate(sentences_to_process):
            if not sent.strip():
                continue
            text_clip_tensor_batch.append(sent)
            if not uses_buffer[sent_num]:
                buffer_start_chunk_index = i
            
                
            start_chunk = buffer_start_chunk_index if uses_buffer[sent_num] else i
            start_time = max(0, (start_chunk * chunk_duration + time_stamps[sent_num][0] if not uses_buffer[sent_num] else buffer_start_time) - 3)
            end_time = start_chunk * chunk_duration + time_stamps[sent_num][1] if not uses_buffer[sent_num] else min( i * chunk_duration + time_stamps[0][1], total_duration)

            curr_meta = {
                "source_id": str(source_id),
                "chunk_index_start": start_chunk,
                "chunk_index_end": i,
                "sentence_index": sent_num,
                "embedding_type": "text",
                "video_filename": os.path.basename(video_path) if is_video else video_path,
                "video_path_relative": os.path.relpath(video_path, os.path.dirname(config.OUTPUT_DIR)),
                "embedding_filename": f"{db_name}_{source_id}_chunk_{i:04d}_{sent_num:04d}.txt",
                "total_scenes": len(audio_chunks),
                "start_frame": int(start_time * video_fps),
                "end_frame": int(end_time * video_fps),
                "start_time_sec": round(start_time, 3),  # Each chunk is 10 seconds, so start time is chunk index * 10
                "end_time_sec": round(end_time, 3),  # Use actual duration for last chunk
                "text": sent,
                "no_speech_prob": no_speech_probs[sent_num]
            }
            text_clip_metadata_batch.append(curr_meta)
            aud_trans_debug.append(curr_meta)
            
        if text_buffer:
            buffer_start_chunk_index = i
            buffer_start_time = i * chunk_duration + time_stamps[-1][0] if sentences else 0
            duration += time_stamps[-1][1] - time_stamps[-1][0]
            # print(f"Duration for this chunk:{text_buffer}:   ", duration)
        else:
            duration = 0 
            
        # Batchwise indexing
        if len(text_clip_tensor_batch) >= AUDIO_BATCH_SIZE:
            text_embeddings = get_text_embedding_batch(text_clip_tensor_batch, model, tokenizer, device, AUDIO_BATCH_SIZE)
            text_embeddings_np = text_embeddings.cpu().numpy() if text_embeddings is not None else None
            # print("Text embeddings shape:", text_embeddings_np.shape)
            faiss.normalize_L2(text_embeddings_np)
            current_idx = text_index.ntotal
            ids = np.arange(current_idx, current_idx + len(text_embeddings_np), dtype='int64')
            text_index.add_with_ids(text_embeddings_np, ids)
            # Store metadata in database
            for j, metadata in enumerate(text_clip_metadata_batch):
                metadata['faiss_id'] = current_idx + j

            db_manager.insert_metadata_batch(text_clip_metadata_batch, db_name)

            # Save FAISS index
            if text_index is not None:
                if not save_index(index_files['text'], text_index):
                    config.indexing_status['errors'].append("Failed to save text index")
            
            text_clip_tensor_batch = []
            text_clip_metadata_batch = []
        
        # current_hours = OFFLINE_LICENSE_LIMIT_HOURS - duration_in_hours
        # OFFLINE_LICENSE_LIMIT_HOURS = max(0.0, current_hours)
        # update_usage_hours(OFFLINE_LICENSE_LIMIT_HOURS)

        config.indexing_status["scenes_processed"] += 1

    if text_buffer.strip():
        final_sent = text_buffer.strip()
        text_clip_tensor_batch.append(final_sent)
        start_time = max(0, buffer_start_time - 3, (len(audio_chunks) -1) * chunk_duration - 3)
        end_time = total_duration
        curr_meta = {
            "source_id": str(source_id),
            "chunk_index_start": buffer_start_chunk_index,
            "chunk_index_end": len(audio_chunks) - 1,
            "sentence_index": 0,
            "embedding_type": "text",
            "video_filename": os.path.basename(video_path) if is_video else video_path,
            "video_path_relative": os.path.relpath(video_path, os.path.dirname(config.OUTPUT_DIR)),
            "embedding_filename": f"{db_name}_{source_id}_chunk_{i:04d}.txt",
            "total_scenes": len(audio_chunks),
            "start_time_sec": round(start_time, 3),  # Each chunk is 10 seconds, so start time is chunk index * 10
            "end_time_sec": round(end_time, 3),  # Use actual duration for last chunk
            "start_frame": int(start_time * video_fps),
            "end_frame": int(end_time * video_fps),
            "text": final_sent,
            "no_speech_prob": no_speech_probs[-1] if no_speech_probs else 0
        }
        text_clip_metadata_batch.append(curr_meta)
        aud_trans_debug.append(curr_meta)

    # Process any remaining audio embeddings in the batch
    if text_clip_tensor_batch:
        text_embeddings = get_text_embedding_batch(text_clip_tensor_batch, model, tokenizer, device, AUDIO_BATCH_SIZE)
        text_embeddings_np = text_embeddings.cpu().numpy() if text_embeddings is not None else None
        # print("Text embeddings shape:", text_embeddings_np.shape)
        faiss.normalize_L2(text_embeddings_np)
        current_idx = text_index.ntotal
        ids = np.arange(current_idx, current_idx + len(text_embeddings_np), dtype='int64')
        text_index.add_with_ids(text_embeddings_np, ids)
        
        # Store metadata in database
        for j, metadata in enumerate(text_clip_metadata_batch):
            metadata['faiss_id'] = current_idx + j

        db_manager.insert_metadata_batch(text_clip_metadata_batch, db_name)

    # Save FAISS index if we have any updates
    if text_index is not None:
        if not save_index(index_files['text'], text_index):
            config.indexing_status['errors'].append("Failed to save text index")
    # Save the debug audio transcript file
    debug_transcript_path = os.path.join(debug_dir, f"{video_name}_transcripts.json")
    with open(debug_transcript_path, 'w') as f:
        json.dump({f"{video_name}": aud_trans_debug}, f, indent=4)
    del text_model
    return

def run_indexing_process(video_files, sourceIds, video_fps_list, use_audio_list, is_video=True, scene_frames=None, db_name= "_default_db"):
    global vidReader, prevProcessedVideo
    online = is_online()

    # Reset all status counters at the start
    config.indexing_status['in_progress'] = True
    config.indexing_status['start_time'] = time.time()
    config.indexing_status['video_queue'] = len(video_files)
    config.indexing_status['errors'] = []
    config.indexing_status['overall_scenes_processed'] = 0
    config.indexing_status['overall_total_scenes'] = 0

    succesfully_indexed = 0

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    index = None
    index_files = get_index_files(db_name)
    
    # Load indices for video, audio, and text
    video_index = load_index(index_files['video'])
    
    # Use video index as the main one
    index = video_index
    # print(f"Loaded video index with {index.ntotal} entries")
    # Get database manager
    db_manager = get_db_manager()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        model, tokenizer, _ = get_languagebind_model(device)
        
        if model is None:
            
            config.indexing_status['errors'].append("Failed to load model")
            config.indexing_status['in_progress'] = False
            return
    except Exception as e:

        config.indexing_status['errors'].append(f"Failed to load model: {str(e)}")
        config.indexing_status['in_progress'] = False
        return

    current_clip_tensor_batch = []
    current_clip_metadata_batch = []
    new_usage_hours = 0.0
    embedding_dim = 768
    res = faiss.StandardGpuResources() if torch.cuda.is_available() else None
    if index is None:
        index = faiss.IndexIDMap(faiss.IndexFlatIP(embedding_dim))
    video_idx = 0

    for source_id, video_path, video_fps, use_audio in zip(sourceIds, video_files, video_fps_list, use_audio_list):
        print(f"Processing video {video_idx + 1}/{len(video_files)}: {video_path}")
        video_filename = os.path.basename(video_path)
        config.indexing_status['current_video'] = video_filename
        config.indexing_status['scenes_processed'] = 0
        scenes, video_frame_rate = detect_scenes(video_path, source_id, config.SCENE_DETECT_THRESHOLD, is_video, video_fps, scene_frames)
        print("Extracted", len(scenes), "scenes from", video_filename)
        config.indexing_status['total_scenes'] = len(scenes)
        config.indexing_status["overall_total_scenes"] += len(scenes)
        if use_audio:
            index_audio_and_text(video_path, source_id, is_video, db_name, video_fps)
        # Get existing metadata for this video from DB
        existing_metadata = db_manager.get_metadata_by_source_id_and_type(source_id, "video", db_name)
        # print(existing_metadata)
        existing_embeddings_count = len(existing_metadata)
        # print("existing_embeddings_count", existing_embeddings_count)
        if len(scenes) == existing_embeddings_count and len(scenes) > 0:
            # print("All scenes already indexed for this video, skipping:", video_filename)
            # If already indexed, count these scenes as processed
            config.indexing_status['scenes_processed'] += len(scenes)
            config.indexing_status["overall_scenes_processed"] += len(scenes)
            config.indexing_status['video_queue'] -= 1
            succesfully_indexed += 1
            video_idx += 1
            continue
        else:
            embedding_filenames = [item.get('embedding_filename') for item in existing_metadata]
        if not scenes or video_frame_rate <= 0:
            config.indexing_status['errors'].append(f"Failed scene detection for {video_filename}")
            # Still count this video as processed, but no scenes
            # config.indexing_status['processed_videos'] += 1
            config.indexing_status['video_queue'] -= 1
            video_idx += 1
            # config.indexing_status['total_scenes'] += len(scenes)
            continue
        
        # config.indexing_status['total_scenes'] += len(scenes)
        succesfully_indexed_clips = 0
        for i, (start_timecode, end_timecode) in enumerate(scenes):
            try:
                scene_idx = i + 1
                embedding_filename = f"{db_name}_{source_id}_sc{scene_idx:04d}_emb"
                if embedding_filename in embedding_filenames:
                    config.indexing_status['scenes_processed'] += 1
                    config.indexing_status["overall_scenes_processed"] += 1
                    # print("skipping already indexed scene:", embedding_filename)
                    continue
                start_sec = start_timecode.get_seconds()
                end_sec = end_timecode.get_seconds()
                start_frame = start_timecode.get_frames()
                end_frame = end_timecode.get_frames()
                duration_sec = end_sec - start_sec
                duration_in_hours = duration_sec / 3600.0
                if duration_sec > 0:
                    new_usage_hours += duration_in_hours
                    
                else:
                    print(f"Invalid scene duration for {video_filename} (scene {scene_idx}), skipping...")
                    continue
                try:
                    frames = sample_frames(video_path, source_id, start_sec, end_sec, config.FRAMES_PER_CLIP_FOR_EMBEDDING, video_frame_rate, is_video)
                except Exception as e:
                    if isinstance(e, DECORDError):
                        vidReader = VideoReader(video_path, ctx=cpu(0), num_threads=1)
                        frames = sample_frames(video_path, source_id, start_sec, end_sec, config.FRAMES_PER_CLIP_FOR_EMBEDDING, video_frame_rate, is_video)
                    else:
                        config.indexing_status['errors'].append(f"Error processing scene {i+1} in {video_filename}: {str(e)}")
                        frames = []
                if len(frames) != config.FRAMES_PER_CLIP_FOR_EMBEDDING:
                    print(f"Warning: Expected {config.FRAMES_PER_CLIP_FOR_EMBEDDING} frames, but got {len(frames)} for {video_filename} (scene {scene_idx}), skipping...")
                    config.indexing_status['errors'].append(f"Expected {config.FRAMES_PER_CLIP_FOR_EMBEDDING} frames, but got {len(frames)} for {video_filename} (scene {scene_idx}), skipping...")
                    continue
                if not len(frames):
                    print(f'len of frames is {len(frames)}')
                    continue
                clip_tensor = preprocess_frames_for_batch(frames)
                if clip_tensor is None:
                    print(f'clip_tensor is none for {video_filename} (scene {scene_idx}), skipping...')
                    continue

                clip_metadata = {
                    "source_id": str(source_id),
                    "video_filename": secure_filename(video_filename),
                    "video_path_relative": os.path.relpath(video_path, os.path.dirname(config.OUTPUT_DIR)),
                    "total_scenes": len(scenes),
                    "scene_index": scene_idx,
                    "start_frame": int(start_frame),
                    "end_frame": int(end_frame),
                    "start_time_sec": round(start_sec, 3),
                    "end_time_sec": round(end_sec, 3),
                    "duration_sec": round(duration_sec, 3),
                    "embedding_filename": embedding_filename,
                    "embedding_type": "video",
                }
                current_clip_tensor_batch.append(clip_tensor)
                current_clip_metadata_batch.append(clip_metadata)

                todays_date = datetime.now()
                if todays_date > config.EXPIRYDATE or todays_date < config.STARTDATE or todays_date < get_recent_date():
                    config.indexing_status['errors'].append("Licence Expired")
                    config.indexing_status['in_progress'] = False
                    print("Licence Expired, please contact support")
                    return

                if (config.RECENT_DATE.year == todays_date.year and config.RECENT_DATE.month < todays_date.month) or config.RECENT_DATE.year < todays_date.year:
                    # print("resetting to 1000 hours")
                    check_licence_validation()
                    config.OFFLINE_LICENSE_LIMIT_HOURS = config.MONTHLY_RENEWAL_CREDITS
                
                config.RECENT_DATE = todays_date
                set_recent_date(config.RECENT_DATE)

                succesfully_indexed_clips += 1
                config.indexing_status['scenes_processed'] += 1
                config.indexing_status["overall_scenes_processed"] += 1

                # Only increment scenes_processed when actually processed (after batch)
                if len(current_clip_tensor_batch) >= config.BATCH_SIZE:
                    # Update license hours
                    current_hours = config.OFFLINE_LICENSE_LIMIT_HOURS - new_usage_hours
                    config.OFFLINE_LICENSE_LIMIT_HOURS = max(0.0, current_hours)
                    update_usage_hours(new_usage_hours)
                    if config.OFFLINE_LICENSE_LIMIT_HOURS <= 0:
                        config.indexing_status['errors'].append("Usage limit exceeded please renew your licence")
                        config.indexing_status['in_progress'] = False
                        print("Usage limit exceeded, please contact support")
                        return
                    process_embedding_batch_faiss(
                        current_clip_tensor_batch,
                        current_clip_metadata_batch,
                        model,
                        device,
                        index,
                        db_name
                    )

                    try:
                        index_files = get_index_files(db_name)
                        
                        # Save video embeddings
                        if not save_index(index_files['video'], index):
                            config.indexing_status['errors'].append("Failed to save video index")
                        
                    except Exception as e:
                        config.indexing_status['errors'].append(f"Failed to save FAISS index and metadata: {str(e)}")
                    
                    # Increment scenes_processed by the number of scenes in this batch
                    current_clip_tensor_batch = []
                    current_clip_metadata_batch = []
                    new_usage_hours = 0.0

            except Exception as e:
                config.indexing_status['errors'].append(f"Error processing scene {i+1} in {video_filename}: {str(e)}")
                # If a scene fails, do not increment scenes_processed
        
        config.indexing_status['processed_videos'] += 1
        config.indexing_status['video_queue'] -= 1
        if succesfully_indexed_clips > 0:
            succesfully_indexed += 1
        video_idx += 1
        vidReader = None   
        prevProcessedVideo = None 

    # Process any remaining batch
    if current_clip_tensor_batch:
        # Update license hours
        current_hours = config.OFFLINE_LICENSE_LIMIT_HOURS - new_usage_hours
        config.OFFLINE_LICENSE_LIMIT_HOURS = max(0.0, current_hours)
        update_usage_hours(new_usage_hours)
        if config.OFFLINE_LICENSE_LIMIT_HOURS <= 0:
            config.indexing_status['errors'].append("Usage limit exceeded please renew your licence")
            config.indexing_status['in_progress'] = False
            print("Usage limit exceeded, please contact support")
            return
        process_embedding_batch_faiss(
            current_clip_tensor_batch,
            current_clip_metadata_batch,
            model,
            device,
            index,
            db_name
        )

        try:
            index_files = get_index_files(db_name)
        
            # Convert indices to CPU if needed
            if torch.cuda.is_available():
                video_index_cpu = faiss.index_gpu_to_cpu(index)
            else:
                video_index_cpu = index

            # Save video embeddings
            if not save_index(index_files['video'], video_index_cpu):
                config.indexing_status['errors'].append("Failed to save video index")
                
        except Exception as e:
            config.indexing_status['errors'].append(f"Failed to save indices: {str(e)}") 
    
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    # config.indexing_status['processed_videos'] += len(video_files)
    config.indexing_status['in_progress'] = False
    # total_hours_indexed = get_total_hours()
    # print("Total indexed hours:", total_hours_indexed)
    config.prevResults = None
    config.prevAudioResults = None
    config.prevImageResults = None
    print(f"Indexing completed, Given: {len(video_files)} videos, Successfully Indexed: {succesfully_indexed}, Time Elapsed: {time.time() - config.indexing_status['start_time']} seconds")

def index_videos(filepaths, sourceIds, video_fps_list, use_audio_list, is_video, scene_frames, db_name):

    if not check_licence_validation():
        return {'error': 'License expired or invalid'}, 403
    if config.OFFLINE_LICENSE_LIMIT_HOURS <= 0:
        return {'error': 'Hour credits expired'}, 403
    # if not db_name.endswith(".index"):
    #     db_name = db_name + ".index"
    
    if config.indexing_status['in_progress']:
        return {'error': 'Indexing already in progress'}, 409
    
    if config.removal_in_progress:
        return {'error': 'Removal in progress, cannot start indexing'}, 409

    if not filepaths:
        return {'error': 'No filenames provided'}, 400
    
    if not sourceIds:
        return {'error': 'No sourceIds provided'}, 400
    
    if len(filepaths) != len(sourceIds):
        return {'error': 'Filepaths and SourceIds are of different length'}, 400

    def resolve_path(fp: str) -> str:
        """Return an absolute path.
        - If fp is absolute, use it directly (regardless of existence check).
        - Otherwise join with WORKING_DIR (relative path from API/CLI clients).
        """
        fp = fp.rstrip('/')
        if os.path.isabs(fp):
            return fp
        # Relative path: prepend working dir
        return os.path.join(config.WORKING_DIR, fp)

    video_paths = []
    
    if len(filepaths) > 1:
        for filepath in filepaths:
            src_path = resolve_path(filepath)
            filename = os.path.basename(src_path)
            secure_name = secure_filename(filename)
            
            if os.path.exists(src_path):
                try:
                    video_paths.append(src_path)
                except Exception as e:
                    return {'error': f'Error copying file {secure_name}: {str(e)}'}, 500
            else:
                return {'error': f'File not found: {secure_name}'}, 404
        threading.Thread(target=run_indexing_process, 
                         args=(video_paths, sourceIds, video_fps_list, use_audio_list, is_video , scene_frames, db_name)).start()
        time.sleep(3)
        return {'success': True, 
                        'message': f'Started Indexing {len(video_paths)} videos as a group',
                }, 200
    else:
        file_path = resolve_path(filepaths[0])
        filename = os.path.basename(file_path)

        if not os.path.isfile(file_path) and (is_video or not os.path.isdir(file_path)):
            return {'error': f'File not found or directory invalid: {file_path}'}, 404
        threading.Thread(target=run_indexing_process, 
                         args=([file_path], sourceIds, video_fps_list, use_audio_list, is_video, scene_frames, db_name)).start()
        time.sleep(3)
        
        return {'success': True, 'message': f'Started Indexing {filename}'}, 200
    