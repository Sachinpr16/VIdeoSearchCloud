from utils.base import *
from utils.licence import check_licence_validation
from model import get_languagebind_image_model, get_text_embedding, get_languagebind_model
from config import get_config
from utils.search import get_faiss_data, get_indices_distances
import io

import copy

# Get the global configuration instance
config = get_config()


def search_registered_api(character, action, threshold, startIndex, limit, dbName, sourceIds=None, image_sim_threshold=0.3, character_weight = 0.6):
    """
    Search across embeddings with support for different index types (video/audio/text)
    Args:
        index_type: One of 'video', 'audio', or 'text' to determine which index to search
    """
    print("#"*20)
    print("Search Registered API called with query:", character + " " + action)
    start_time = time.time()

    # image_sim_threshold = 0.3
    # print("Image similarity threshold:", image_sim_threshold)
    if startIndex < 1:
        startIndex = 1
    if limit <= 0:
        limit = 20
    startIndex -= 1  # Convert to 0-based index

    if sourceIds and isinstance(sourceIds, list):
        sourceIds = [str(sid) for sid in sourceIds]  # Ensure all are strings
    elif sourceIds is None or sourceIds == []:
        sourceIds = None  # Keep current logic
    
    if not check_licence_validation():
        return {'error': 'License expired or invalid'}, 403
    
    if not character.strip():
        return {'error': 'Character cannot be empty'}, 400
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, tokenizer, _ = get_languagebind_model()
    if model is None or tokenizer is None:
        return {'error': 'Failed to load model for search'}, 500

    db_manager = get_db_manager()
    all_db_names = db_manager.get_all_databases()
    if not all_db_names:
        return {'error': 'No databases found. Please index videos first.'}, 404

    #can be optimized
    # print("Retrieved registered images metadata:", data)
    results = []
    existing_scenes = []
    #get characters which are in quotes, can be in single quotes or double quotes

    query_idx = None
    quoted_chars = character.strip().casefold()
    data = db_manager.get_image_register_metadata_by_name(quoted_chars)
    if data:
        query_idx = data.get('index')
    # for it_name, item in data.items():
    #     if quoted_chars and item['name'].casefold() == quoted_chars.casefold():
    #         query_idx = item['index']
    #         break
    modified_query = action.strip() if action else ""
    print("Modified query after removing quoted characters:", modified_query)
    query_embedding_np = None
    if query_idx is not None and modified_query:
        query_embedding = get_text_embedding(modified_query, model, tokenizer, device)
        if query_embedding is not None:
            query_embedding_np = query_embedding.cpu().numpy()
            faiss.normalize_L2(query_embedding_np)
    if query_idx is not None:
        if os.path.exists(os.path.join(config.WORKING_DIR, "database", "images_register.index")):
            image_index = faiss.read_index(os.path.join(config.WORKING_DIR, "database", "images_register.index"))
            index_map = faiss.vector_to_array(image_index.id_map)
            query_idx_internal = np.where(index_map == query_idx)[0]
            # print("Internal index found for query:", query, "internal index:", query_idx_internal)
            if len(query_idx_internal) == 0:
                return {'error': f'No registered image found for character: {character}'}, 404
            query_idx_internal = int(query_idx_internal[0])
            image_embedd_np = image_index.index.reconstruct(query_idx_internal).reshape(1, -1)
        else:
            query_idx = None
        
    if query_idx is None and quoted_chars:
        return {'error': f'No registered image found for query: {quoted_chars}'}, 404
    
    db_names = all_db_names if dbName == "*" else [dbName]
    for db_name in db_names:
        data, dbFileName = get_faiss_data(db_name, "video")
        # print(f"Searching in database: {db_name}, index file: {dbFileName}")
        index = data.get('index')
        # metadata = data.get('metadata', {})
        # print(f"Index has {index.ntotal} entries and metadata has {len(metadata)} items")
        if index is None:
            continue
        indices = [[]]
        distances = [[]]
        try:
            k = startIndex+limit + 100
            if query_idx is not None:
                # search using image embedding
                # distances, indices = index.search(image_embedd_np, 1000)
                indices, distances = get_indices_distances(index, image_embedd_np, 5000, sourceIds, db_manager, db_name, "video")
                valid_indices_list = [idx for idx in indices[0] if idx != -1]
                metadata = db_manager.get_metadata_by_database_faiss_ids_dict(db_name, valid_indices_list, "video")
                # print("len of results:", len(valid_indices_list))
                # print("performing character-based search", end =" ")
                if modified_query:
                    # print("Modified query after removing character name:", modified_query)
                    # Filter candidates based on image similarity threshold
                    candidate_ids = indices[0][distances[0] > image_sim_threshold]
                    filtered_distances = distances[0][distances[0] > image_sim_threshold]
                    # print("len of filtered distances:", len(filtered_distances))
                    index_map_main = faiss.vector_to_array(index.id_map)
                    candidate_ids_internal = []
                    filtered_candidates = []
                    filtered_candidate_distances = []
                    for cid, dist in zip(candidate_ids, filtered_distances):
                        internal_id = np.where(index_map_main == cid)[0]
                        if len(internal_id) > 0:
                            candidate_ids_internal.append(int(internal_id[0]))
                            filtered_candidates.append(cid)
                            filtered_candidate_distances.append(dist)
                    if not len(candidate_ids_internal):
                        continue
                    # print(len(filtered_candidates), len(filtered_candidate_distances))
                    # print(filtered_candidate_distances[:10])
                    # print(filtered_candidates[:10])
                    vecs = np.vstack([index.index.reconstruct(int(i)).reshape(1, -1) for i in candidate_ids_internal])
                    temp_index = faiss.IndexFlatIP(index.d)
                    temp_index.add(vecs)
                    # print("len of temp_index:", temp_index.ntotal)
                    distances, local_indices = temp_index.search(query_embedding_np, 1000)
                    indices = np.array([filtered_candidates[i] for i in local_indices[0]]).reshape(1, -1)
                    # print("with some action")
                    for i in range(len(distances[0])):
                        distances[0][i] = (1 - character_weight) * distances[0][i] + character_weight * filtered_candidate_distances[local_indices[0][i]]

            for i, (idx, score) in enumerate(zip(indices[0], distances[0])):
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
        'query': character + " " + action,
        'results': results,
        'total_results': len(results),
        'search_time': search_time
    }, 200


from model import get_image_embedding_batch, get_languagebind_image_model


def register_images(data_list):
   
    config.registration_in_progress = True
    config.registration_errors = []

    if not data_list:
        config.registration_in_progress = False
        print("No data provided for image registration")
        config.registration_errors.append("No data provided for image registration")
        return {'error': 'No data provided'}, 400
    # print("Registering images with data:", data_list)
    model, tokenizer, _ = get_languagebind_image_model()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    index_file = os.path.join(config.WORKING_DIR, "database", 'images_register.index')
    # time.sleep(10)
    db_manager = get_db_manager()
    #get metadata from postgresql
    #metadata_dict = db_manager.get_images_register_metadata()
    # 2. Filter and Load Images (Data Validation)
    processed_items = [] # This will hold only successfully loaded data
    existing_characters_dict = {}
    
    for item in data_list:
        name = item.get('name')
        path_dicts_list = item.get('paths', [])
        if not path_dicts_list:
            print(f"No paths provided for name: {name}. Skipping this entry.")
            config.registration_errors.append(f"No paths provided for name: {name}. Skipping this entry.")
            continue
        name = name.strip().casefold() if name else None

        #check if everything in path_dicts_list has filepath key
        # print(path_dicts_list)
        if not all('filepath' in pd for pd in path_dicts_list) or not all('roi' in pd for pd in path_dicts_list):
            config.registration_in_progress = False
            config.registration_errors.append(f"Invalid data format for name: {name}. Each path item must contain 'filepath' and 'roi'")
            print(f"Invalid data format for name: {name}. Each path item must contain 'filepath' and 'roi'")
            return {'error': f'Invalid data format for name: {name}. Each path item must contain "filepath" and "roi"'}, 400

        paths = [pd.get('filepath') for pd in path_dicts_list]
        rois = [pd.get('roi') for pd in path_dicts_list]

        valid_images_for_this_name = []
        new_paths_added = []

        metadata_character = db_manager.get_image_register_metadata_by_name(name)
        if metadata_character:
            existing_characters_dict[name] = metadata_character
        
        current_existing_paths = set(metadata_character['image_paths']) if metadata_character else set()

        for path, roi in zip(paths, rois):
            full_path = os.path.join(config.WORKING_DIR, path)
            if os.path.exists(full_path) and path not in current_existing_paths and path not in new_paths_added:
                try:
                    img = Image.open(full_path).convert("RGB")
                    print("Roi for image", path, "is", roi)
                    try:
                        if roi:
                            img = img.crop((int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3])))
                    except Exception as e:
                        print(f"Error applying ROI for {path}: {e}. Using full image instead.")
                    valid_images_for_this_name.append(img)
                    new_paths_added.append(path)
                except Exception as e:
                    print(f"Error loading {path}: {e}")
            elif not os.path.exists(full_path):
                print(f"File not found: {full_path}")
                config.registration_errors.append(f"File not found: {full_path}")

        if valid_images_for_this_name:
            processed_items.append({
                'name': name,
                'images': valid_images_for_this_name,
                'new_paths': new_paths_added
            })

    if not processed_items:
        config.registration_in_progress = False
        config.registration_errors.append("No valid images found for registration after processing all items")
        print("No valid images found for registration after processing all items")
        return {'error': 'No new or valid images to register'}, 400

    # 3. Initialize/Load FAISS Index
    d = 768 # Ensure this matches your model output dimension
    if os.path.exists(index_file):
        index = faiss.read_index(index_file)
    else:
        index = faiss.IndexIDMap(faiss.IndexFlatIP(d))
    # 4. Generate Embeddings and Update Index
    for item in processed_items:
        name = item['name']
        # Get embedding for the new batch of images
        new_emb_tensor = get_image_embedding_batch(item['images'], model, device)
        new_emb_np = new_emb_tensor.cpu().numpy().astype('float32')
        faiss.normalize_L2(new_emb_np)

        metadata_character = existing_characters_dict.get(name)
        if metadata_character:
            # meta_idx = existing_map[name]
            old_meta = metadata_character
            old_id = old_meta['index']
            n_old = old_meta['n_images']
            n_new = len(item['new_paths'])
            ids_array = faiss.vector_to_array(index.id_map)
            internal_old_id = np.where(ids_array == old_id)[0]
            if len(internal_old_id) == 0:
                continue
            internal_old_id = internal_old_id[0]
            # Reconstruct old vector to calculate moving average
            old_vec = index.index.reconstruct(int(internal_old_id)).reshape(1, -1)
            
            # Weighted average: (old * count + new * count) / total
            combined_vec = (old_vec * n_old + new_emb_np * n_new) / (n_old + n_new)
            faiss.normalize_L2(combined_vec)

            # Update Index: Remove old and add updated
            index.remove_ids(np.array([old_id], dtype='int64'))
            new_id = old_id # Keep the same ID for consistency
            index.add_with_ids(combined_vec, np.array([new_id], dtype='int64'))

            db_manager.update_image_register_metadata(name, metadata_character['image_paths'] + item['new_paths'], new_id, n_old + n_new)
            
        else:
            # New Entry
            index_map = faiss.vector_to_array(index.id_map)
            new_id = int(max(index_map) + 1 if len(index_map) > 0 else 0)            
            index.add_with_ids(new_emb_np, np.array([int(new_id)], dtype='int64'))
            
            db_manager.add_image_register_metadata(name, item['new_paths'], new_id, len(item['new_paths']))

    # 5. Save Changes
    faiss.write_index(index, index_file)
    # print(index.ntotal," entries in FAISS index after update")
    config.registration_in_progress = False
    return {'success': True, 'message': f'Updated {len(processed_items)} names in database'}, 200

def register_images_api(data_list): 
    print("Register Images API called with data:", data_list)
    if not check_licence_validation():
        return {'error': 'License expired or invalid'}, 403
    if config.registration_in_progress:
        return {'error': 'Image registration already in progress'}, 409
    for item in data_list:
        name = item.get('name')
        name = name.strip() if name else None
        if not name:
            return {'error': 'Each item must have a non-empty "name"'}, 400
        
    threading.Thread(target=register_images, args=(data_list,)).start()
    return {'success': True, 'message': 'Image registration started'}, 200



def remove_registered_character(name):
    
    if not check_licence_validation():
        return {'error': 'License expired or invalid'}, 403
    if config.registration_in_progress:
        return {'error': 'Cannot remove registered character while registration is in progress'}, 409
    db_manager = get_db_manager()
    try:
        # Remove the database metadata
        status = db_manager.remove_image_register_metadata(name)
        if status:
            return {'success': True, 'message': f'Removed registered character "{name}"'}, 200
        else:
            return {'error': f'Character "{name}" not found in registered characters'}, 404
    except Exception as e:
        print(f"Exception in remove_registered_character: {str(e)}")
        return {'error': f'Error removing registered character: {str(e)}'}, 500
    
    

def get_registration_status():

    db_manager = get_db_manager()
    if not check_licence_validation():
        return {'error': 'License expired or invalid'}, 403
    try:
        # metadata_dict = db_manager.get_images_register_metadata()
        registered_characters = db_manager.get_all_registered_character_names()  # Assuming this method returns a list of registered character names
        # for name, meta in metadata_dict.items():
        #     registered_characters.append(name)
        return {
            'registration_in_progress': config.registration_in_progress,
            'registered_characters': registered_characters,
            'total_registered': len(registered_characters),
            'errors': config.registration_errors
        }, 200
    except Exception as e:
        return {'error': f'Error retrieving registration status: {str(e)}'}, 500


