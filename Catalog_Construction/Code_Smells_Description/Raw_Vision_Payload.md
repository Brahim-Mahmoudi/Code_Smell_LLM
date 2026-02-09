# RVP — Raw Vision Payload

## Name & Intent

**Raw Vision Payload (RVP)**

Intent: avoid sending raw, unbounded images to vision-enabled LLMs without preprocessing or explicit control over resolution and detail. Vision inputs consume tokens and strongly affect latency, cost, and accuracy.

## Context

Vision-enabled APIs accept images alongside text. Image size, resolution, and detail level directly affect latency, cost, and how much of the multimodal context window is consumed.

## Problem

Sending full-resolution screenshots or many images increases latency and token usage, can trigger cost spikes and rate-limit issues, and makes it harder for the model to focus on relevant details. Raw screenshots can also leak sensitive UI elements.

## Solution

Treat vision input as a limited resource. Crop to the relevant region, downscale large images, and set an explicit detail level. Avoid sending redundant images and prefer text extraction when the task is primarily textual.

## Effect on Software Quality

### Performance (P)
- Lower latency and cost

### Reliability (R)
- More stable multimodal behavior
- Less risk of truncation and missed details

## Minimal Example (bad -> good)

```python
from openai import OpenAI
client = OpenAI()

# BAD — raw screenshot payload
def describe_bug(screenshot_bytes):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Describe the bug shown in this screenshot."},
                {"type": "input_image", "image": screenshot_bytes}
            ]
        }],
        temperature=0.2
    )
    return response.output[0].content[0].text

# GOOD — crop, resize, and set low detail
def describe_bug(screenshot_bytes):
    small_image = resize_and_crop(screenshot_bytes, max_side=1024)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Describe the bug shown in this screenshot."},
                {"type": "input_image", "image": small_image, "detail": "low"}
            ]
        }],
        temperature=0.2
    )
    return response.output[0].content[0].text
```

## Additional Examples

Anthropic

```python
import base64
import anthropic

client = anthropic.Anthropic()

# BAD — raw image bytes
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe the bug in this screenshot."},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(raw_image).decode()
                }
            }
        ]
    }]
)

# GOOD — preprocessed image
small_image = resize_and_crop(raw_image, max_side=1024)
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe the bug in this screenshot."},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(small_image).decode()
                }
            }
        ]
    }]
)
```

Gemini

```python
from PIL import Image
import google.generativeai as genai

model = genai.GenerativeModel("gemini-1.5-pro")

# BAD — raw high-res image
resp = model.generate_content(["Describe this UI", Image.open("full.png")])

# GOOD — resized image
img = Image.open("full.png")
img.thumbnail((1024, 1024))
resp = model.generate_content(["Describe this UI", img])
```

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
