# Pet Adoption AI

**AI-generated promotional art and videos for shelter pets.**

My wife volunteers at a local pet adoption clinic, and they were having trouble getting pets noticed. I was also looking for a real-world project to test out an end-to-end AI stack — Ollama for local LLM inference, Replicate for FLUX LoRA training, and Flask for tying it together. This was the result: a pipeline that takes a pet's adoption listing + photos, trains a custom model, and generates stylized artwork of that specific animal. A companion video maker turns pet photos into promotional videos with music and text overlays.

## What It Creates

### AI Art (Main Pipeline)

Sample outputs from real shelter pets:

| Jackson | Honey | Yellow | Koda |
|---------|-------|--------|------|
| ![Jackson](sample_outputs/jackson/jackson_1.png) | ![Honey](sample_outputs/honey/honey_1.png) | ![Yellow](sample_outputs/yellow/yellow_1.png) | ![Koda](sample_outputs/koda/koda_1.png) |
| ![Jackson 2](sample_outputs/jackson/jackson_2.png) | ![Honey 2](sample_outputs/honey/honey_2.png) | ![Yellow 2](sample_outputs/yellow/yellow_2.png) | ![Koda 2](sample_outputs/koda/koda_2.png) |

*Each pet's LoRA was trained on 5-20 real photos, then used with style LoRAs (Pixar, Ghibli, etc.) to generate these.*

### Promotional Videos (Video Maker)

The video maker takes pet photos and creates MP4 videos with:
- Ken Burns zoom/pan animation effects
- AI-generated background music via Suno AI
- Text overlays (pet introduction + adoption info)
- Configurable video length and image ordering

---

## Part 1: AI Art Pipeline

### How It Works

Four steps, orchestrated through a Flask web UI:

```
1. GATHER DATA      Paste the pet's adoption listing. Ollama (llama3) extracts
                    name, breed, age, personality traits, writes an adoption
                    story, and generates image prompts.

2. TRAIN A LORA     Upload 5-20 photos of the pet. The app trains a FLUX LoRA
                    on Replicate so the AI learns what this specific pet looks like.
                    (~15-20 min on a GPU-T4)

3. GENERATE ART     Using the trained LoRA + style LoRAs (Pixar, Ghibli, Lego,
                    hand-painted miniature), generates images of the pet in
                    various scenarios based on extracted personality traits.

4. CREATE MORE      A separate page lets you generate additional images with custom
                    prompts, different styles, and aspect ratios.
```

Everything is tracked in a per-pet JSON config, and you get an email with the results when it's done.

### The Web UI

- **Create Pet LoRA** - Paste the adoption description, upload photos, hit go. A live terminal shows progress via WebSocket.
- **Pet Directory** - Browse all processed pets, view their AI art and submission data.
- **Make New Images** - Pick a pet, write a custom prompt, choose a style LoRA (Pixar, Ghibli, etc.), and generate more images.

### Architecture

```
app.py                          Flask + SocketIO web server
0_run_all.py                    Pipeline orchestrator
1_gather_pet_data.py            Ollama-powered data extraction & story generation
2_train_a_lora.py               Replicate FLUX LoRA training
3_create_images_of_pet.py       Automated image generation from trained model
4_create_additional_images.py   On-demand image generation with custom prompts

utilities/
  ollama_utils.py               Local LLM management (install, serve, query)
  replicate_utils.py            Replicate API (model creation, training, inference)
  gmail_utils.py                Email notifications with image attachments
  fileio_utils.py               Temporary file hosting for training uploads
  file_zip_utils.py             Image packaging for upload
  archive_utils.py              Disk space management & output archiving

templates/
  base.html                     Bootstrap 5 layout with SocketIO progress
  create_lora.html              Pet submission form with live progress terminal
  create_images.html            Custom image generation with style controls
  view_pets.html                Gallery view of processed pets
```

### Setup

#### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed locally
- A [Replicate](https://replicate.com/) account (for LoRA training + image generation)
- (Optional) Gmail app password for email notifications

#### Installation

```bash
git clone https://github.com/tillo13/pet-adoption-ai.git
cd pet-adoption-ai

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Pull the local LLM for data extraction
ollama pull llama3

# Configure your API keys
cp .env.example .env
# Edit .env with your Replicate API token and other credentials
```

#### Running

```bash
# Start the web UI
python app.py

# Opens at http://localhost:5001
```

Or run the pipeline directly from the command line:

```bash
# Edit GLOBAL_VARIABLES.py with the pet description, then:
python 0_run_all.py
```

### Configuration

Edit `GLOBAL_VARIABLES.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `STEPS` | 1000 | LoRA training steps |
| `LORA_RANK` | 16 | LoRA rank (higher = more capacity) |
| `RESOLUTION` | "512, 768, 1024" | Training resolutions |
| `NUMBER_OF_FACTS` | 5 | Encouraging facts / image prompts to generate |
| `MODE` | "DEVELOPMENT" | Set to "PRODUCTION" for public models + HuggingFace push |
| `EMAIL_ON_COMPLETION` | True | Send email when generation finishes |

### Cost

Running on Replicate's GPU-T4 hardware:
- **LoRA training**: ~$1-2 per pet (15-20 min at ~$0.00055/sec)
- **Image generation**: ~$0.01-0.03 per image

Processing 7 pets with ~130 total generated images cost roughly $10-15.

### The Pets

This project processed 7 real shelter animals:

| Pet | Type | Images Generated |
|-----|------|-----------------|
| Jackson | Dog | 6 |
| Marina | Dog | 9 |
| Yellow | Cat | 35 |
| Koda | Cat | 10 |
| Mister White | Cat | 8 |
| Maybelline | Cat | 39 |
| Honey | Dog | 25 |

---

## Part 2: Video Maker

The `video_maker/` directory contains a separate pipeline for creating promotional pet videos from photos.

### How It Works

Five sequential steps:

```
1. PREPARE IMAGES    Converts photos to JPEG, corrects orientation, resizes to
                     1280x720 with blurred background fill for portrait images.

2. CREATE MOVIE      Generates an MP4 from the prepared images with configurable
                     duration per image. Optionally generates background music
                     via Suno AI, or uses a provided MP3 file.

3. APPLY ZOOMPAN     Adds Ken Burns-style zoom and pan animation effects to
                     make the slideshow feel cinematic.

4. ADD TEXT           Overlays introduction text (first 5 seconds) and adoption
                     info text (last 5 seconds) with styled fonts and shadows.

5. CLEAN UP          Removes temporary files and intermediate video segments.
```

### Video Maker Architecture

```
video_maker/
  run_all.py                    Pipeline orchestrator (runs steps 1-5 in order)
  1_prepare_images.py           Image conversion, EXIF orientation, resize
  2_create_movie.py             FFmpeg video creation + Suno AI music integration
  3_apply_zoompan.py            Ken Burns zoom/pan effects via FFmpeg
  4_add_text.py                 Text overlays with FFmpeg drawtext filters
  5_clean_up.py                 Temporary file cleanup
  GLOBAL_VARIABLES.py           Song prompt, text overlays, video settings
  testsuno.py                   Suno AI API connectivity test
```

### Video Maker Prerequisites

- Python 3.8+
- [FFmpeg](https://ffmpeg.org/) installed and on PATH
- [Pillow](https://pillow.readthedocs.io/) (`pip install Pillow`)
- (Optional) [Suno AI](https://suno.com/) account for AI-generated music
- (Optional) Local [suno-api](https://github.com/gcui-art/suno-api) npm server for music generation

### Video Maker Usage

```bash
cd video_maker

# 1. Put pet photos in initial_images/
# 2. Edit GLOBAL_VARIABLES.py with pet name, adoption info, and song settings
# 3. Run the pipeline:
python run_all.py

# Output video will be in created_videos/
```

### Video Maker Configuration

Edit `video_maker/GLOBAL_VARIABLES.py`:

| Setting | Description |
|---------|-------------|
| `SONG_PROMPT` | Text prompt for Suno AI music generation |
| `SONG_TO_USE` | Path to an existing MP3 (leave empty to auto-generate) |
| `FIRST_5_SECOND_TEXT` | Text shown at the start of the video |
| `LAST_5_SECONDS_TEXT` | Text shown at the end (e.g., adoption clinic address) |
| `DEFAULT_VIDEO_LENGTH` | Target video length in seconds |
| `randomize_images` | Shuffle image order (True/False) |

---

## Tech Stack

**AI Art Pipeline:**
- **Local LLM**: Ollama + llama3 for text extraction and prompt generation
- **Image training**: Replicate API for FLUX LoRA fine-tuning
- **Image generation**: Replicate API with trained LoRA + style LoRAs
- **Web UI**: Flask + Flask-SocketIO + Bootstrap 5
- **File hosting**: file.io for ephemeral training image uploads
- **Notifications**: Gmail SMTP with optional GCP Secret Manager

**Video Maker:**
- **Video processing**: FFmpeg (video creation, zoom/pan, text overlays)
- **Image handling**: Pillow (orientation correction, resize, blur backgrounds)
- **Music**: Suno AI API for background music generation
- **Orchestration**: Sequential Python scripts via subprocess

## License

MIT
