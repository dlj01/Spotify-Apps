import sys
from datetime import datetime
import time

''' modules '''
import top_tracks
import recent_tracks
import gui


''' MAIN '''
if __name__ == "__main__":
    # Create Playlist Objects
    current_date = datetime.now().strftime("%m/%d/%Y")
    rotation = {
        'name': "rotation",
        'desc': f"My top tracks of the last month (as of {current_date})",
        'time_range': "short_term",
        'num_tracks': 50
    }
    mid_rotation = {
        'name': "mid rotation",
        'desc': f"My top tracks of the last 6 months (as of {current_date})",
        'time_range': "medium_term",
        'num_tracks': 100
    }
    lost_in_rotation = {
        'name': "lost in rotation",
        'desc': f"My top tracks of the last year (as of {current_date})",
        'time_range': "long_term",
        'num_tracks': 100
    }
    top_lists = [
        rotation,
        mid_rotation,
        lost_in_rotation
    ]

    # Update
    top = top_tracks.TopTracks(top_lists)
    top.update()
    #time.sleep(5)
    #rewind = recent_tracks.Rewind()
    #rewind.update()

    sys.exit()