import os
import cv2

def migrate_existing_videos():
    video_dir = "static/videos"
    if not os.path.exists(video_dir):
        print("No videos directory found.")
        return
        
    for filename in os.listdir(video_dir):
        if filename.endswith(".mp4"):
            path = os.path.join(video_dir, filename)
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                print(f"Could not open {filename}")
                continue
                
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "".join([chr((fourcc >> (8 * i)) & 0xFF) for i in range(4)])
            cap.release()
            
            print(f"File: {filename} has codec: {codec}")
            if codec.lower() not in ['avc1', 'h264']:
                print(f"Migrating {filename} from {codec} to avc1...")
                temp_path = path + ".tmp.mp4"
                cap = cv2.VideoCapture(path)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
                
                fourcc_avc1 = cv2.VideoWriter_fourcc(*'avc1')
                out = cv2.VideoWriter(temp_path, fourcc_avc1, fps, (width, height))
                if out.isOpened():
                    frame_count = 0
                    while cap.isOpened():
                        ret, frame = cap.read()
                        if not ret:
                            break
                        out.write(frame)
                        frame_count += 1
                    cap.release()
                    out.release()
                    cap_check = cv2.VideoCapture(temp_path)
                    if cap_check.isOpened():
                        cap_check.release()
                        os.remove(path)
                        os.rename(temp_path, path)
                        print(f"Migrated {filename} successfully ({frame_count} frames)!")
                    else:
                        cap_check.release()
                        print(f"Failed to verify migrated temp video for {filename}")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                else:
                    print(f"Failed to open avc1 VideoWriter for {filename}")
                    cap.release()
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

if __name__ == "__main__":
    migrate_existing_videos()
