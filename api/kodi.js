# Add this to the top of your api/kodi.py file:
from .episode_detector import EpisodeDetector

# Initialize detector globally
episode_detector = EpisodeDetector()

# In your main API handler function, add this processing:
def process_results_with_episode_detection(raw_results):
    """Process results and add episode range information"""
    enhanced_results = []
    
    for result in raw_results:
        title = result.get('title', '')
        file_count = result.get('torrent_files', 0)  # From your database query
        total_size = result.get('total_size', 0)     # From your database query
        
        # Detect episode range
        episode_range = episode_detector.detect_episode_range(title, file_count, total_size)
        
        # Add enhanced fields
        result['episode_range'] = episode_range
        result['display_title'] = episode_detector.format_display_title(
            title, episode_range, result.get('size_formatted', '')
        )
        
        enhanced_results.append(result)
    
    return enhanced_results

# In your main API handler, call this function:
# raw_results = your_existing_database_query(query, limit)
# enhanced_results = process_results_with_episode_detection(raw_results)
# return {'success': True, 'data': enhanced_results, 'count': len(enhanced_results)}
