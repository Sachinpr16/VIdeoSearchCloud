from utils.base import *
from utils.licence import check_licence_validation
from config import get_config

# Get the global configuration instance
config = get_config()


def get_indexed_videos():
    """Get a list of all indexed videos and their metadata from the database"""
    proc_videos = 0
    proc_audios = 0
    partially_proccessed = 0

    # Get database manager and get grouped metadata
    db_manager = get_db_manager()
    db_groups = db_manager.get_indexed_files_by_db_and_type()
    for db_name, db_data in db_groups.items():
        proc_videos += len(db_data.get('video', []))
        proc_audios += len(db_data.get('text', []))
        partially_proccessed += len(db_data.get('partial', []))
    config.indexing_status['processed_videos'] = proc_videos
    config.indexing_status['processed_audios'] = proc_audios
    config.indexing_status['partially_processed'] = partially_proccessed
    return db_groups


def get_status():
    if not check_licence_validation():
        return {'error': 'License expired or invalid'}, 403
    elapsed = 0
    if config.indexing_status['start_time'] > 0 and config.indexing_status['in_progress']:
        elapsed = int(time.time() - config.indexing_status['start_time'])
    indexed_video_list = get_indexed_videos()
    return {
        'remaining_credits': config.OFFLINE_LICENSE_LIMIT_HOURS,
        'in_progress': config.indexing_status['in_progress'],
        'current_video': config.indexing_status['current_video'],
        'processed_videos': config.indexing_status['processed_videos'],
        'processed_audios': config.indexing_status['processed_audios'],
        # 'partially_processed': config.indexing_status['partially_processed'],
        'video_queue': config.indexing_status['video_queue'],
        'cv_scenes_processed': config.indexing_status['scenes_processed'],
        'cv_total_scenes': config.indexing_status['total_scenes'], 
        # 'overall_scenes_processed': config.indexing_status['overall_scenes_processed'],
        # 'overall_total_scenes': config.indexing_status['overall_total_scenes'],
        'elapsed_time': elapsed,
        'errors': config.indexing_status['errors'],
        "indexed_data" : indexed_video_list
    }
