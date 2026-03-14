import audio_engine

# Replace these with actual paths on your computer to test
folders = [
    r"C:\Music\FolderA", 
    r"C:\Music\FolderB"
]

for folder in folders:
    audio_engine.process_directory(folder)

print("Sequence complete!")
