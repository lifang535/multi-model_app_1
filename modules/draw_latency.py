import re
import matplotlib.pyplot as plt
from datetime import datetime

# Read and process the log file
log_file_path = 'logs/latency.log'
video_start_times = {}
video_end_times = {}

with open(log_file_path, 'r') as f:
    lines = f.readlines()
    for line in lines:
        match = re.search(r'video_(\d+) (start|end) at (\d+\.\d+)', line)
        if match:
            video_num = int(match.group(1))
            event_type = match.group(2)
            timestamp = float(match.group(3))
            
            if event_type == 'start':
                video_start_times[video_num] = timestamp
            elif event_type == 'end':
                video_end_times[video_num] = timestamp

# Calculate latencies and prepare data for plotting
video_nums = sorted(video_start_times.keys())
latencies = [(video_end_times[video_num] - video_start_times[video_num]) for video_num in video_nums]

# Plotting
plt.figure(figsize=(10, 6))
plt.plot(video_nums, latencies, marker='o')
plt.xlabel('Video')
plt.ylabel('Latency')
plt.title('Video Latency')
plt.xticks(video_nums, [f'video_{num}' for num in video_nums])
plt.grid(True)
plt.show()
