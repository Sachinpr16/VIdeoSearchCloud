from utils.base import *
from utils.licence import check_licence_validation
from config import get_config

# Get the global configuration instance
config = get_config()

def remove_index(sourceId, database_name, index_type='both'):
    db_manager = get_db_manager()
    index_files = get_index_files(database_name)

    if index_type in ['video', 'both']:
            #check if there is any index files for the database, if not return
        if not os.path.exists(index_files['video']):
            print(f"No video index file found for database {database_name} at {index_files['video']}, skipping video index update for source {sourceId}")
            return
        else:
            video_index = load_index(index_files['video'])
            if video_index is not None:
                # Get all faiss_ids for the source from metadata
                faiss_ids = db_manager.get_faiss_ids_by_source_id_and_type(sourceId, 'video', database_name)
                if faiss_ids:
                    faiss_ids_arr = np.array(faiss_ids, dtype='int64')
                    video_index.remove_ids(faiss_ids_arr)
                    fake_vecs = np.zeros((len(faiss_ids_arr), video_index.d), dtype='float32')
                    video_index.add_with_ids(fake_vecs, faiss_ids_arr)     
                if not save_index(index_files['video'], video_index):
                        print(f"Error saving updated video index after replacing vectors for source {sourceId}")

    if index_type in ['text', 'both']:
        if not os.path.exists(index_files['text']):
            print(f"No text index file found for database {database_name} at {index_files['text']}, skipping text index update for source {sourceId}")
            return
        else:
            text_index = load_index(index_files['text'])
            if text_index is not None:
                faiss_ids = db_manager.get_faiss_ids_by_source_id_and_type(sourceId, 'text', database_name)
                if faiss_ids:
                    faiss_ids_arr = np.array(faiss_ids, dtype='int64')
                    text_index.remove_ids(faiss_ids_arr)
                    fake_vecs = np.zeros((len(faiss_ids_arr), text_index.d), dtype='float32')
                    text_index.add_with_ids(fake_vecs, faiss_ids_arr)   
                if not save_index(index_files['text'], text_index):
                        print(f"Error saving updated text index after replacing vectors for source {sourceId}")

def remove_video(sourceId, db_name, index_type='both'):
    """
    Remove a video and its associated metadata from the database and note that the FAISS index needs rebuilding.
    Args:
        sourceId: The unique identifier of the video to remove
        db_name: The database name to remove from
        index_type: The type of indices to update ('video', 'text', or 'both')
    """
    # if db_name and not db_name.endswith(".index"):
    #     db_name = db_name + ".index"

    config.removal_in_progress = True
    
    if not check_licence_validation():
        config.removal_in_progress = False
        return {'error': 'License expired or invalid'}, 403
    if not sourceId:
        config.removal_in_progress = False
        return {'error': 'No sourceId provided'}, 400
    if config.indexing_status['in_progress']:
        config.removal_in_progress = False
        return {'error': 'Cannot remove videos while indexing is in progress'}, 409

    db_manager = get_db_manager()
    
    # Get database name from filename and handle type-specific deletions
    database_name = db_name.replace('.index', '') if db_name else None
    removed_count = 0
    
    try:
        # set the vectors of the removed indices to fake vector that won't be returned in search results
        if db_name is None:
            dbs = db_manager.get_all_databases()
            for db in dbs:
                remove_index(sourceId, db, index_type)
        else:
            remove_index(sourceId, db_name, index_type)

        if index_type == 'both':
            # Remove all metadata for the source
            removed_count = db_manager.remove_metadata_by_source_id_and_type(sourceId, database_name)
        else:
            # Only remove metadata of specific type
            removed_count = db_manager.remove_metadata_by_source_id_and_type(sourceId, database_name, index_type)

        if removed_count == 0:
            config.removal_in_progress = False
            return {'message': f'No clips found for video with Source ID {sourceId} of type {index_type}', 'removed': 0}, 200

        # Reset search results cache
        config.prevResults = None
        config.prevAudioResults = None
        config.prevImageResults = None
        config.removal_in_progress = False
        return {
            'success': True,
            'message': f'Removed {sourceId} from {index_type} index',
            'removed_clips': removed_count,
            # 'note': f'FAISS {index_type} index may need rebuilding for optimal performance'
        }, 200
        
    except Exception as e:
        return {'error': f'Error removing video: {str(e)}'}, 500 
    