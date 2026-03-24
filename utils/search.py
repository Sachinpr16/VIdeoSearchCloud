from utils.base import *
from utils.licence import check_licence_validation
from model import get_languagebind_image_model, get_image_embedding, get_audio_embedding, get_languagebind_audio_model, get_text_embedding, get_languagebind_model
from config import get_config
import io

import copy

# Get the global configuration instance
config = get_config()


def get_faiss_data(dbName, index_type): 
    db_manager = get_db_manager()
    index_files = get_index_files(dbName) 
    file_path = index_files[index_type]
    try:
        if os.path.exists(file_path):
            # Load FAISS index
            index = faiss.read_index(file_path)
            # Get metadata from PostgreSQL
            return [{'index': index}, os.path.basename(file_path)]
        else:
            print(f"FAISS index file not found: {file_path}")
            return [{'index': None}, None]
    except Exception as e:
        print(f"Error loading FAISS data from {file_path}: {e}")
        return [{'index': None}, None]


prevQuery = None
# config.prevResults = None
prevDbName = None
prevSourceIds = None
prevIndexType = None

def get_indices_distances(index, query_embedding_np, k, sourceIds, db_manager, db_name, index_type):
    # print("sourceIds:", sourceIds)
    if sourceIds is not None:
        try:
            faiss_ids_dict = db_manager.get_faiss_ids_by_source_ids_and_type(sourceIds, index_type, db_name)
            faiss_ids_exist = False
            for sid, fids in faiss_ids_dict.items():
                if fids:
                    faiss_ids_exist = True
                    break
            if faiss_ids_exist:
                #create empty faiss_ids_array 
                faiss_ids_array = []
                d = index.d 
                ids_array = faiss.vector_to_array(index.id_map)
                temp_index = faiss.IndexFlatIP(d) # Use L2 for Euclidean distance, IndexFlatIP for dot product/cosine
                for source_id in sourceIds:
                    curr_faiss_ids = faiss_ids_dict.get(source_id, [])
                    for fid in curr_faiss_ids:
                        internal_fid = np.where(ids_array == fid)[0]
                        if len(internal_fid)==0:
                            continue
                        internal_fid = internal_fid[0]
                        vector = index.index.reconstruct(int(internal_fid)).reshape(1, -1)
                        temp_index.add(vector)
                        faiss_ids_array.append(fid)
                faiss_ids_array = np.array(faiss_ids_array, dtype='int64')
                # print("len of temp_index:", temp_index.ntotal)
                distances, local_indices = temp_index.search(query_embedding_np, k)
                indices = [faiss_ids_array[local_indices[0]]]
            else:
                distances = np.array([[]] , dtype='float32')
                indices = np.array([[]], dtype='int64')
        except Exception as e:
            distances, indices = index.search(query_embedding_np, k)
    else:
        distances, indices = index.search(query_embedding_np, k)
    
    return indices, distances

def search_api(query, threshold, startIndex, limit, dbName, sourceIds=None, index_type='video'):
    """
    Search across embeddings with support for different index types (video/audio/text)
    Args:
        index_type: One of 'video', 'audio', or 'text' to determine which index to search
    """
    global prevQuery, prevDbName, prevSourceIds, prevIndexType
    start_time = time.time()

    if startIndex < 1:
        startIndex = 1
    if limit <= 0:
        limit = 20
    startIndex -= 1  # Convert to 0-based index
    
    if not os.listdir(os.path.join(config.WORKING_DIR, "database")) or not os.path.exists(os.path.join(config.WORKING_DIR, "database")):
        config.prevResults = None

    if sourceIds and isinstance(sourceIds, list):
        sourceIds = [str(sid) for sid in sourceIds]  # Ensure all are strings
    elif sourceIds is None or sourceIds == []:
        sourceIds = None  # Keep current logic
    
    if prevQuery != query:
        prevQuery = query
    elif config.prevResults is not None and prevQuery == query and (startIndex+limit) <= len(config.prevResults) and prevDbName == dbName and prevSourceIds == sourceIds and prevIndexType == index_type:
        results = config.prevResults

        # Apply sourceIds filtering to cached results if needed
        if sourceIds is not None:
            results = [result for result in results if result['metadata'].get('source_id') in sourceIds]

        results.sort(key=lambda x: x['score'], reverse=True)
        
        startIndex = max(0, startIndex)
        endIndex = min(startIndex + limit, len(results))
        results = results[startIndex:endIndex]
        for result in results:
            metadata = result['metadata']
            metadata["result_number"] = startIndex + results.index(result) + 1
            result = {
                "score": result['score'],
                "metadata": metadata
            }
        
        search_time = time.time() - start_time
        return {
            'query': query,
            'results': results,
            'total_results': len(results),
            'search_time': search_time
        }, 200
    
    if not check_licence_validation():
        return {'error': 'License expired or invalid'}, 403
    
    if not query:
        config.prevResults = None
        return {'error': 'Query cannot be empty'}, 400
    
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, tokenizer, _ = get_languagebind_model()
    if model is None or tokenizer is None:
        return {'error': 'Failed to load model for search'}, 500

    db_manager = get_db_manager()
    all_db_names = db_manager.get_all_databases()
    if not all_db_names:
        return {'error': 'No databases found. Please index videos first.'}, 404
    
    query_embedding = get_text_embedding(query, model, tokenizer, device)
    if query_embedding is None:
        return {'error': 'Failed to generate query embedding'}, 500

    query_embedding_np = query_embedding.cpu().numpy()
    faiss.normalize_L2(query_embedding_np)

    results = []
    existing_scenes = []
    if index_type == 'video':
        db_names = all_db_names if dbName == "*" else [dbName]
        for db_name in db_names:
            data, dbFileName = get_faiss_data(db_name, index_type)
            # print(f"Searching in database: {db_name}, index file: {dbFileName}")
            index = data.get('index')
            #metadata = data.get('metadata', {}) #need_change
            # print(f"Index has {index.ntotal} entries and metadata has {len(metadata)} items")
            if index is None:
                continue
            try:
                k = startIndex+limit + 100
                indices, distances = get_indices_distances(index, query_embedding_np, k, sourceIds, db_manager, db_name, index_type)
                valid_indices_list = [idx for idx in indices[0] if idx != -1]
                metadata = db_manager.get_metadata_by_database_faiss_ids_dict(db_name, valid_indices_list, index_type)
                for i, (idx, score) in enumerate(zip(indices[0], distances[0])):
                    # print(idx, score)
                    if idx < 0 :
                        continue  
                    if score > threshold: 
                        metadata_item = metadata.get(idx)
                        if metadata_item is None:
                            continue 
                        if sourceIds is not None:
                            if metadata_item.get('source_id') not in sourceIds:
                                continue  # Skip this result if source_id not in allowed list

                        if metadata_item.get('embedding_filename', "") not in existing_scenes:
                            results.append({
                                "score": float(score),  
                                "metadata": metadata_item
                            })
                            existing_scenes.append(metadata_item['embedding_filename'])
            except Exception as e:
                print(f'Error searching with FAISS: {str(e)}')
    elif index_type == 'text':
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        db_names = all_db_names if dbName == "*" else [dbName]
        for db_name in db_names:
            data, dbFileName = get_faiss_data(db_name, index_type)
            # print(f"Searching in database: {db_name}, index file: {dbFileName}")
            index = data.get('index')
            # print(f"Index has {index.ntotal} entries and metadata has {len(metadata)} items")
            if index is None :
                continue
                
            try:
                k = startIndex+limit + 100
                indices, distances = get_indices_distances(index, query_embedding_np, k, sourceIds, db_manager, db_name, index_type)
                valid_indices_list = [idx for idx in indices[0] if idx != -1]
                metadata = db_manager.get_metadata_by_database_faiss_ids_dict(db_name, valid_indices_list, index_type)
                for i, (idx, score) in enumerate(zip(indices[0], distances[0])):
                    if idx < 0 :
                        continue  
                    if score > threshold: 
                        metadata_item = metadata.get(idx)
                        if metadata_item is None:
                            continue 
                        # Filter by sourceIds if provided
                        if sourceIds is not None:
                            if metadata_item.get('source_id') not in sourceIds:
                                continue  # Skip this result if source_id not in allowed list
                        if metadata_item.get('embedding_filename', "") not in existing_scenes:
                            results.append({
                                "score": float(score),  
                                "metadata": metadata_item
                            })
                            existing_scenes.append(metadata_item['embedding_filename'])
            except Exception as e:
                print(f'Error searching with FAISS: {str(e)}')

    config.prevResults = copy.deepcopy(results)
    prevDbName = dbName
    prevSourceIds = sourceIds
    prevIndexType = index_type

    results.sort(key=lambda x: x['score'], reverse=True)
    
    startIndex = max(0, startIndex)
    endIndex = min(startIndex + limit, len(results))
    results = results[startIndex:endIndex]
    for result in results:
        metadata = result['metadata']
        metadata["result_number"] = startIndex + results.index(result) + 1
        result = {
            "score": result['score'],
            "metadata": metadata
        }
    
    search_time = time.time() - start_time
    # print(results)
    return {
        'query': query,
        'results': results,
        'total_results': len(results),
        'search_time': search_time
    }, 200


prevImageQuery = None
# config.prevImageResults = None
prevImageDbName = None
prevImageSourceIds = None

prevAudioQuery = None
# config.prevAudioResults = None
prevAudioDbName = None
prevAudioSourceIds = None

def imagesearch_api(image_path, threshold, startIndex, limit, dbName, sourceIds=None):
    global prevImageQuery, prevImageDbName, prevImageSourceIds
    image_path = os.path.join(config.WORKING_DIR, image_path)
    start_time = time.time()
    filename = image_path.split("/")[-1]
    if startIndex < 1:
        startIndex = 1
    if limit <= 0:
        limit = 20
    startIndex -= 1  # Convert to 0-based index
    # if dbName != "*" and (not dbName.endswith(".pkl")):
    #     dbName = dbName + ".pkl"

    # Handle sourceIds filtering
    if sourceIds and isinstance(sourceIds, list):
        sourceIds = [str(sid) for sid in sourceIds]  # Ensure all are strings
    elif sourceIds is None or sourceIds == []:
        sourceIds = None  # Keep current logic

    if prevImageQuery != image_path:
        prevImageQuery = image_path
    elif prevImageQuery == image_path and config.prevImageResults is not None and (startIndex+limit) <= len(config.prevImageResults) and prevImageDbName == dbName and prevImageSourceIds == sourceIds:
        # print("Using cached results for query:", image_path)
        results = config.prevImageResults

        # Apply sourceIds filtering to cached results if needed
        if sourceIds is not None:
            results = [result for result in results if result['metadata'].get('source_id') in sourceIds]

        results.sort(key=lambda x: x['score'], reverse=True)
        startIndex = max(0, startIndex)
        endIndex = min(startIndex + limit, len(results))
        # print("Start Index:", startIndex, "End Index:", endIndex, "Total Results:", len(results), "limit:", limit)
        results = results[startIndex:endIndex]
        for result in results:
            metadata = result['metadata']
            metadata["result_number"] = startIndex + results.index(result) + 1
            result = {
                "score": result['score'],
                "metadata": metadata
            }
        search_time = time.time() - start_time
        return {
            'query': filename,
            'results': results,
            'total_results': len(results),
            'search_time': search_time
        }, 200
    with open(image_path, 'rb') as image_file:
        image_bytes = image_file.read()
    model, tokenizer, _ = get_languagebind_image_model()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # print("database name", dbName)
    if model is None:
        return {'error': 'Failed to load model for search'}, 500
    if image_bytes:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img = img.convert("RGB")
            try:
                query_embedding = get_image_embedding(img, model, device)
                if query_embedding is None:
                    return {'error': 'Failed to generate query embedding'}, 500
            except Exception as e:
                return {'error': f'Error generating query embedding: {str(e)}'}, 500
            query_embedding_np = query_embedding.cpu().numpy()
            faiss.normalize_L2(query_embedding_np)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            db_manager = get_db_manager()
            all_db_names = db_manager.get_all_databases()
            if not all_db_names:
                return {'error': 'No databases found. Please index videos first.'}, 404
            results = []
            existing_scenes = []
            db_names = all_db_names if dbName == "*" else [dbName]
            for db_name in db_names:
                data, dbFileName = get_faiss_data(db_name, "video")
                # print(f"Searching in database: {db_name}, index file: {dbFileName}")
                index = data.get('index') 
                if index is None:
                    continue

                k = startIndex+limit + 100
                indices, distances = get_indices_distances(index, query_embedding_np, k, sourceIds, db_manager, db_name, "video")
                valid_indices_list = [idx for idx in indices[0] if idx != -1]
                metadata = db_manager.get_metadata_by_database_faiss_ids_dict(db_name, valid_indices_list, "video")
                res_no = 0
                for i, (idx, score) in enumerate(zip(indices[0], distances[0])):
                    # print(idx, score)
                    if idx < 0 or score <= threshold:
                        continue
                    if score > threshold: 
                        metadata_item = metadata.get(idx)
                        if metadata_item is None:
                            continue 
                    # Filter by sourceIds if provided
                    if sourceIds is not None:
                        if metadata_item.get('source_id') not in sourceIds:
                            continue  # Skip this result if source_id not in allowed list
                    if float(metadata_item["duration_sec"]) < 2:
                        continue
                    res_no += 1
                    metadata_item['result_number'] = res_no
                    if metadata_item['embedding_filename'] not in existing_scenes:
                        results.append({
                            "score": float(score),
                            "metadata": metadata_item
                        })
                        existing_scenes.append(metadata_item['embedding_filename'])
            
            results.sort(key=lambda x: x['score'], reverse=True)
            config.prevImageResults = copy.deepcopy(results)
            prevImageDbName = dbName
            prevImageSourceIds = sourceIds
            startIndex = max(0, startIndex)
            endIndex = min(startIndex + limit, len(results))
            results = results[startIndex:endIndex]
            for result in results:
                metadata = result['metadata']
                metadata["result_number"] = startIndex + results.index(result) + 1
                result = {
                    "score": result['score'],
                    "metadata": metadata
                }
            search_time = time.time() - start_time
            return {
                'query': filename,
                'results': results,
                'total_results': len(results),
                'search_time': search_time
            }, 200
        except Exception as e:
            return {'error': f'Error in image search: {str(e)}'}, 500

def audiosearch_api(audio_path, threshold, startIndex, limit, dbName, sourceIds=None):
    global prevAudioQuery, prevAudioDbName, prevAudioSourceIds
    audio_path = os.path.join(config.WORKING_DIR, audio_path)
    start_time = time.time()
    if startIndex < 1:
        startIndex = 1
    if limit <= 0:
        limit = 20
    startIndex -= 1  # Convert to 0-based index
    # if dbName != "*" and (not dbName.endswith(".pkl")):
    #     dbName = dbName + ".pkl"

    # Handle sourceIds filtering
    if sourceIds and isinstance(sourceIds, list):
        sourceIds = [str(sid) for sid in sourceIds]  # Ensure all are strings
    elif sourceIds is None or sourceIds == []:
        sourceIds = None  # Keep current logic

    if prevAudioQuery != audio_path:
        prevAudioQuery = audio_path
    elif prevAudioQuery == audio_path and config.prevAudioResults is not None and (startIndex+limit) <= len(config.prevAudioResults) and prevAudioDbName == dbName and prevAudioSourceIds == sourceIds:
        # print("Using cached results for query:", audio_path)
        results = config.prevAudioResults

        # Apply sourceIds filtering to cached results if needed
        if sourceIds is not None:
            results = [result for result in results if result['metadata'].get('source_id') in sourceIds]
        
        
        results.sort(key=lambda x: x['score'], reverse=True)
        startIndex = max(0, startIndex)
        endIndex = min(startIndex + limit, len(results))
        # print("Start Index:", startIndex, "End Index:", endIndex, "Total Results:", len(results), "limit:", limit)
        results = results[startIndex:endIndex]
        for result in results:
            metadata = result['metadata']
            metadata["result_number"] = startIndex + results.index(result) + 1
            result = {
                "score": result['score'],
                "metadata": metadata
            }
        search_time = time.time() - start_time
        return {
            'query': audio_path.split("/")[-1],
            'results': results,
            'total_results': len(results),
            'search_time': search_time
        }, 200
    with open(audio_path, 'rb') as audio_file:
        audio_bytes = audio_file.read()
    # print(audio_bytes)
    model, tokenizer, _ = get_languagebind_audio_model()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # if dbName != "*" and (not dbName.endswith(".pkl")):
    #     dbName = dbName + ".pkl"
    if model is None:
        return {'error': 'Failed to load model for search'}, 500
    if audio_bytes:
        try:
            try:
                query_embedding = get_audio_embedding(audio_bytes, model, device)
                if query_embedding is None:
                    return {'error': 'Failed to generate query embedding'}, 500
            except Exception as e:
                return {'error': f'Error generating query embedding: {str(e)}'}, 500
            query_embedding_np = query_embedding.cpu().numpy()
            faiss.normalize_L2(query_embedding_np)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            db_manager = get_db_manager()
            all_db_names = db_manager.get_all_databases()
            if not all_db_names:
                return {'error': 'No databases found. Please index videos first.'}, 404
            results = []
            existing_scenes = []
            db_names = all_db_names if dbName == "*" else [dbName]
            for db_name in db_names:
                data, dbFileName = get_faiss_data(db_name, "video")
                # print(f"Searching in database: {db_name}, index file: {dbFileName}")
                index = data.get('index')
                if index is None:
                    continue

                k = startIndex+limit + 100
                indices, distances = get_indices_distances(index, query_embedding_np, k, sourceIds, db_manager, db_name, "video")
                valid_indices_list = [idx for idx in indices[0] if idx != -1]
                metadata = db_manager.get_metadata_by_database_faiss_ids_dict(db_name, valid_indices_list, "video")
                # distances /= 40
                res_no = 0
                for i, (idx, score) in enumerate(zip(indices[0], distances[0])):
                    # print(idx, score)
                    if idx < 0 or score <= threshold:
                        continue
                    if score > threshold:
                        metadata_item = metadata.get(idx)
                        if metadata_item is None:
                            continue

                     # Filter by sourceIds if provided
                    if sourceIds is not None:
                        if metadata_item.get('source_id') not in sourceIds:
                            continue  # Skip this result if source_id not in allowed list

                    if float(metadata_item["duration_sec"]) < 2:
                        continue
                    res_no += 1
                    metadata_item['result_number'] = res_no
                    if metadata_item['embedding_filename'] not in existing_scenes:
                        results.append({
                            "score": float(score),
                            "metadata": metadata_item
                        })
                        existing_scenes.append(metadata_item['embedding_filename'])
            
            results.sort(key=lambda x: x['score'], reverse=True)
            config.prevAudioResults = copy.deepcopy(results)
            prevAudioDbName = dbName
            prevAudioSourceIds = sourceIds
            startIndex = max(0, startIndex)
            endIndex = min(startIndex + limit, len(results))
            results = results[startIndex:endIndex]
            for result in results:
                metadata = result['metadata']
                metadata["result_number"] = startIndex + results.index(result) + 1
                result = {
                    "score": result['score'],
                    "metadata": metadata
                }
            search_time = time.time() - start_time
            return {
                'query': audio_path.split("/")[-1],
                'results': results,
                'total_results': len(results),
                'search_time': search_time
            }, 200
        except Exception as e:
            return {'error': f'Error in audio search: {str(e)}'}, 500

def get_transcripts(sourceId, db_name=None):
    db_manager = get_db_manager()
    try:
        transcripts = db_manager.get_transcripts_by_source_id(sourceId, db_name)
        return transcripts, 200
    except Exception as e:
        return {'error': f'Error retrieving transcripts: {str(e)}'}, 500