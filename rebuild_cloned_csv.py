import csv
from pathlib import Path
from Bible import Bible

def rebuild_cloned_csv():
    """Rebuild cloned.csv by scanning the cloned audio directory"""
    
    # Initialize Bible
    bible = Bible()
    audio_ai = bible.audio.audioai
    
    # Get cloned directory
    cloned_dir = bible.audio.cloned_directory
    
    # List all MP3 files in the directory
    mp3_files = list(cloned_dir.glob("*.mp3"))
    print(f"Found {len(mp3_files)} MP3 files in {cloned_dir}")
    
    # Process each file
    processed_count = 0
    for mp3_file in mp3_files:
        try:
            # Parse filename: "001.001.001.mp3"
            filename = mp3_file.stem  # Remove extension
            parts = filename.split('.')
            
            if len(parts) != 3:
                print(f"Warning: Unexpected filename format: {filename}")
                continue
                
            book_num = int(parts[0])
            chapter_num = int(parts[1])
            verse_num = int(parts[2])
            
            # Get duration
            duration = bible.audio.get_audio_duration(mp3_file)
            
            # Save using AudioAI's method
            audio_ai.save_cloned_duration(book_num, chapter_num, verse_num, duration)
            
            processed_count += 1
            
            # Progress indicator
            if processed_count % 100 == 0:
                print(f"Processed {processed_count} files...")
                
        except Exception as e:
            print(f"Error processing {mp3_file.name}: {e}")
    
    print(f"\n✅ Rebuilt cloned.csv with {processed_count} entries")

if __name__ == "__main__":
    rebuild_cloned_csv()