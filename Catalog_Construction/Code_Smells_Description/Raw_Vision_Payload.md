# Code Smell: Raw Vision Payload (RVP)

## Definition

**Raw Vision Payload (RVP)** is an anti-pattern that occurs when raw, unprocessed images are sent directly to vision-enabled LLMs (GPT-4 Vision, Claude Vision, Gemini Pro Vision) without preprocessing or explicit control over resolution and detail level.

## Motivation

Vision-enabled models allow sending images (screenshots, diagrams, photos) alongside text, but the size, resolution, and detail level of images directly affect:

- **Latency** and response time
- **Cost** per API call (images consume many tokens)
- **Context window** usage
- **Model focus** and accuracy
- **Privacy** and compliance risks

Not managing vision payloads explicitly can lead to:
- **Cost spikes** from unnecessarily large token consumption
- **Latency issues** from processing high-resolution images
- **Rate limit exhaustion** when sending multiple large images
- **Model focus problems** when critical details are lost in large screenshots
- **Privacy leaks** from unfiltered interface elements
- **Context truncation** that's opaque to developers

## Impact

Sending raw, unbounded vision payloads causes:
- Unpredictable and potentially prohibitive costs
- Degraded performance and slow response times
- Inefficient use of context window
- Security and privacy risks
- Difficulty debugging and optimizing

## Examples

###  Bad Practices
```python
# Full resolution screenshot without preprocessing
def analyze_ui(screenshot_path):
    with open(screenshot_path, 'rb') as f:
        image_bytes = f.read()
    
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this UI"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
                    }
                }
            ]
        }]
    )

# Multiple unprocessed images
def compare_screens(screenshots):
    images = [
        {"type": "image_url", "image_url": {"url": img}} 
        for img in screenshots
    ]
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[{
            "role": "user",
            "content": [{"type": "text", "text": "Compare"}] + images
        }]
    )

# Claude with raw image
response = anthropic.messages.create(
    model="claude-3-opus-20240229",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": raw_image_data  # Raw data!
                }
            }
        ]
    }]
)

# LangChain with unprocessed vision
from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4-vision-preview")
result = llm.invoke([
    HumanMessage(content=[
        {"type": "text", "text": "Describe this image"},
        {"type": "image_url", "image_url": screenshot_url}  # Raw URL!
    ])
])
```

### ✅ Good Practices
```python
# Preprocessed image with detail control
def analyze_ui(screenshot_path):
    # Explicit preprocessing
    image = Image.open(screenshot_path)
    image = crop_to_relevant_area(image, region=(100, 100, 800, 600))
    image = resize_with_aspect_ratio(image, max_side=1024)
    
    buffered = BytesIO()
    image.save(buffered, format="PNG", optimize=True)
    image_bytes = buffered.getvalue()
    
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this UI"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}",
                        "detail": "low"  # Explicit detail setting
                    }
                }
            ]
        }]
    )

# Budget-aware image processing
MAX_IMAGE_SIZE = 1024
MAX_FILE_SIZE_MB = 2

def process_image_with_budget(image_path):
    """Process image within defined budgets."""
    image = Image.open(image_path)
    
    # Check file size
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        # Aggressive compression
        quality = int(80 * (MAX_FILE_SIZE_MB / file_size_mb))
    else:
        quality = 85
    
    # Resize if needed
    if max(image.size) > MAX_IMAGE_SIZE:
        image.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.Resampling.LANCZOS)
    
    # Optimize
    buffered = BytesIO()
    image.save(buffered, format="JPEG", quality=quality, optimize=True)
    return buffered.getvalue()

# Context-appropriate detail settings
def describe_bug(screenshot_bytes):
    """Bug description needs low detail."""
    small_image = resize_and_crop(screenshot_bytes, max_side=1024)
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe the bug shown"},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(small_image).decode()
                    }
                }
            ]
        }],
        # Appropriate configuration for simple task
        max_tokens=500
    )

def analyze_fine_details(diagram_bytes):
    """Technical diagram needs high resolution."""
    optimized_image = resize_and_crop(diagram_bytes, max_side=2048)
    response = client.messages.create(
        model="claude-3-opus-20240229",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze technical details"},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(optimized_image).decode()
                    }
                }
            ]
        }]
    )

# Text extraction instead of screenshot
def extract_error_message(error_screenshot):
    """Extract text instead of sending full screenshot."""
    # Use OCR or text extraction
    text = extract_text_from_image(error_screenshot)
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": f"Explain this error: {text}"
        }]
    )

# Multiple images with filtering
def compare_screens(screenshots):
    """Process multiple images with budget."""
    # Limit number of images
    selected = screenshots[:3]  # Max 3 images
    
    # Process each image
    processed = [
        {
            "type": "image_url",
            "image_url": {
                "url": process_and_encode(img, max_side=800),
                "detail": "low"
            }
        }
        for img in selected
    ]
    
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Compare these screens"}
            ] + processed
        }]
    )
```

### Helper Functions
```python
from PIL import Image
from io import BytesIO
import base64

def resize_and_crop(image_bytes, max_side=1024, crop_region=None):
    """Resize and optionally crop image to budget."""
    image = Image.open(BytesIO(image_bytes))
    
    # Crop to relevant region if specified
    if crop_region:
        image = image.crop(crop_region)
    
    # Resize maintaining aspect ratio
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    
    # Return optimized bytes
    buffered = BytesIO()
    image.save(buffered, format="PNG", optimize=True)
    return buffered.getvalue()

def validate_image_budget(image_bytes, max_mb=5):
    """Validate image against size budget."""
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > max_mb:
        raise ValueError(
            f"Image exceeds budget: {size_mb:.2f}MB > {max_mb}MB"
        )
    return True

def crop_to_relevant_area(image, region):
    """Crop to relevant area."""
    return image.crop(region)

def resize_with_aspect_ratio(image, max_side):
    """Resize while preserving aspect ratio."""
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return image
```

## Detail Level Guidelines by Task
```python
IMAGE_DETAIL_CONFIGS = {
    # Low detail level
    "ui_description": {
        "detail": "low",
        "max_side": 1024,
        "use_cases": ["General UI description", "Coarse inspection"]
    },
    "bug_report": {
        "detail": "low",
        "max_side": 1024,
        "use_cases": ["Bug reporting", "Error screenshots"]
    },
    "general_content": {
        "detail": "low",
        "max_side": 800,
        "use_cases": ["General content analysis", "Classification"]
    },
    
    # High detail level
    "technical_diagram": {
        "detail": "high",
        "max_side": 2048,
        "use_cases": ["Technical diagrams", "Complex schematics"]
    },
    "ocr_extraction": {
        "detail": "high",
        "max_side": 2048,
        "use_cases": ["Text extraction", "Document reading"]
    },
    "fine_analysis": {
        "detail": "high",
        "max_side": 1920,
        "use_cases": ["Detailed analysis", "Precise inspection"]
    }
}

def get_image_config(task_type):
    """Get appropriate configuration for task type."""
    return IMAGE_DETAIL_CONFIGS.get(
        task_type,
        {"detail": "low", "max_side": 1024}  # Default
    )
```

## Detection Strategy

RVP detection can be formulated as a structural check of vision API calls:

1. **AST parsing**: Analyze source code and build syntax tree
2. **Identify vision calls**: Detect `chat.completions.create` with image content, `messages.create` with image type, `generate_content` with image parts
3. **Verify image content**: Look for `type: "image"`, `type: "image_url"`, base64 data, image URLs
4. **Check preprocessing**: Look for resize functions, cropping, dimension constraints, size validation
5. **Check detail level**: Look for `detail` parameter with explicit values
6. **Detection logic**: Report RVP when call uses vision model AND contains image content AND lacks preprocessing AND lacks explicit detail configuration
7. **Smart exclusions**: Ignore calls with preprocessed images, constrained image sources, thumbnail generation flows
8. **Report**: `WARNING: Unbounded vision payload at line N`

## Recommendations

### Essential Rules

1. **Always preprocess images** before sending to vision APIs
2. **Set explicit detail levels** based on requirements:
   - `low`: UI descriptions, general content, coarse inspection
   - `high`: Fine-grained analysis, technical diagrams, OCR
   - `auto`: Let provider decide (avoid for reproducibility)
3. **Define image budgets**:
   - Maximum resolution (e.g., 1024x1024 for low, 2048x2048 for high)
   - Maximum file size (e.g., 2-5MB per image)
   - Maximum number of images per request (e.g., 3-5)

### Best Practices

4. **Crop to relevant regions** instead of sending full screenshots
5. **Extract text when possible** instead of sending screenshots of text
6. **Document image budgets** alongside other resource limits
7. **Monitor token usage** from vision inputs to optimize costs
8. **Implement preprocessing helpers** for consistent image handling
9. **Consider privacy** when sending screenshots (filter sensitive data)
10. **Test with realistic images** to validate budget effectiveness

## Limitations

Static detection has several limitations:

- **Cannot detect** all image preprocessing in external libraries
- **May not recognize** custom optimization utilities
- **Conservative on dynamic pipelines** where images are processed elsewhere
- **Cannot validate** if preprocessing is adequate for the use case
- **Misses** detail settings passed through configuration files
- **Cannot detect** when images are pre-optimized before reaching the code

## Typical Costs
```python
# Cost comparison example (GPT-4 Vision)

# High-resolution image (4K) without preprocessing
# ~1500 image tokens = ~$0.045 per image

# Preprocessed image (1024x1024, low detail)
# ~85 image tokens = ~$0.0025 per image

# Savings: ~94% cost reduction per image
```

## Validation Checklist

Before sending an image to a vision LLM:

- [ ] Is the image resized to an appropriate resolution?
- [ ] Is the detail level explicitly defined?
- [ ] Is the relevant region isolated (cropping)?
- [ ] Does the file size respect the defined budget?
- [ ] Are sensitive data filtered if necessary?
- [ ] Is the number of images per request limited?
- [ ] Is token usage monitored?
- [ ] Would text extraction be more appropriate?

### Sources

***Papers***

- J. Lee, W. Shin, S. Yang, K.-U. Song, D. Lim, J. Kim, T.-H. Kim, and B.-K. Kim. 2025. ERGO: Efficient High-Resolution Visual Understanding for Vision-Language Models. arXiv:2509.21991. https://doi.org/10.48550/arXiv.2509.21991

- P. K. A. Vasu, F. Faghri, C.-L. Li, C. Koc, N. True, A. Antony, G. Santhanam, J. Gabriel, P. Grasch, O. Tuzel, and H. Pouransari. 2024. FastVLM: Efficient Vision Encoding for Vision Language Models. arXiv:2412.13303. https://doi.org/10.48550/arXiv.2412.13303

- J. Qian, C. Wang, Y. Yang, C. Zhang, H. Jiang, X. Luo, Y. Kang, Q. Lin, A. Zhang, S. Jiang, T. Cao, T. Mao, S. Banerjee, G. Liu, S. Rajmohan, D. Zhang, Y. Yang, Q. Zhang, and L. Qiu. 2025. Zoomer: Adaptive Image Focus Optimization for Black-box MLLM. arXiv:2505.00742. https://doi.org/10.48550/arXiv.2505.00742

***Official Documentation***

None in our evidence base for RVP.

***Engineering Blogs***

None in our evidence base for RVP.

***Grey Literature***

None in our evidence base for RVP.
