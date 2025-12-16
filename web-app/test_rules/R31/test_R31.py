import ast
import unittest
import sys
import os

# Ensure the generated_rules_R30 module in the same directory is importable
sys.path.insert(0, os.path.dirname(__file__))
import generated_rules_R31  # The file generated for rule R30 (Reasoning Effort Not Explicitly Set)


class TestGeneratedRules31(unittest.TestCase):
    def setUp(self):
        # Capture reported messages
        self.messages = []

        def report(message):
            self.messages.append(message)

        # Monkey-patch the report function in the generated module
        generated_rules_R31.report = report

    def run_rule(self, code: str):
        """Parse code and run the R31 rule on its AST."""
        self.messages.clear()
        tree = ast.parse(code)
        # make sure parent pointers exist
        if hasattr(generated_rules_R31, "add_parent_info"):
            generated_rules_R31.add_parent_info(tree)
        generated_rules_R31.rule_R31(tree)

    # ========== TRUE POSITIVES - OpenAI API (should report RAW VISION PAYLOAD) ==========

    def test_openai_raw_screenshot_bytes_no_preprocessing(self):
        """OpenAI: Sending raw screenshot bytes without preprocessing -> REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()
response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Describe this screenshot"},
            {"type": "input_image", "image": screenshot_bytes}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for raw image bytes without preprocessing")

    def test_openai_raw_image_without_detail_level(self):
        """OpenAI: Sending image without explicit detail level -> REPORT."""
        code = """
import openai
resp = openai.ChatCompletion.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Analyze this"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for image without detail level")

    def test_openai_multiple_raw_images(self):
        """OpenAI: Sending multiple raw images without preprocessing -> REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()
response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Compare these"},
            {"type": "input_image", "image": image1_bytes},
            {"type": "input_image", "image": image2_bytes}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for multiple raw images")

    def test_openai_full_resolution_screenshot(self):
        """OpenAI: Full resolution screenshot without size limits -> REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()

def analyze_ui(screenshot):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Find the bug"},
                {"type": "input_image", "image": screenshot}
            ]
        }]
    )
    return response
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for full resolution screenshot")

    def test_openai_image_url_http_no_detail(self):
        """OpenAI: HTTP image URL without detail level -> REPORT."""
        code = """
import openai
resp = openai.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for HTTP URL without detail level")

    def test_openai_data_uri_no_preprocessing(self):
        """OpenAI: Data URI image without preprocessing -> REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()
data_uri = f"data:image/jpeg;base64,{base64_image}"
response = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe"},
            {"type": "image_url", "image_url": {"url": data_uri}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for data URI without preprocessing")

    def test_openai_image_with_detail_auto(self):
        """OpenAI: Image with detail set to 'auto' (not explicit) -> REPORT."""
        code = """
import openai
resp = openai.ChatCompletion.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's this?"},
            {"type": "image_url", "image_url": {"url": image_url, "detail": "auto"}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Should report 'auto' detail as it's not an explicit choice")

    # ========== TRUE POSITIVES - Anthropic API ==========

    def test_anthropic_raw_image_base64(self):
        """Anthropic: Raw image bytes in base64 -> REPORT."""
        code = """
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Analyze this screenshot"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": raw_image_data}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for Anthropic raw image")

    def test_anthropic_multiple_images_no_preprocessing(self):
        """Anthropic: Multiple raw images -> REPORT."""
        code = """
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=2048,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Compare these images"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img1_data}},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img2_data}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for multiple Anthropic raw images")

    def test_anthropic_image_url_no_preprocessing(self):
        """Anthropic: Image URL without preprocessing -> REPORT."""
        code = """
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What do you see?"},
            {"type": "image", "source": {"type": "url", "url": "https://example.com/image.png"}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for Anthropic image URL without preprocessing")

    # ========== TRUE POSITIVES - Google Gemini API ==========

    def test_gemini_raw_image_inline_data(self):
        """Gemini: Raw image with inline_data -> REPORT."""
        code = """
import google.generativeai as genai
model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate_content([
    "Describe this image",
    {"mime_type": "image/png", "data": raw_bytes}
])
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for Gemini raw image")

    def test_gemini_multiple_images_no_preprocessing(self):
        """Gemini: Multiple raw images -> REPORT."""
        code = """
import google.generativeai as genai
model = genai.GenerativeModel("gemini-pro-vision")
response = model.generate_content([
    "Compare these screenshots",
    {"mime_type": "image/jpeg", "data": screenshot1},
    {"mime_type": "image/jpeg", "data": screenshot2},
    {"mime_type": "image/jpeg", "data": screenshot3}
])
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for multiple Gemini images")

    def test_gemini_file_path_no_preprocessing(self):
        """Gemini: Image file path without preprocessing -> REPORT."""
        code = """
import google.generativeai as genai
model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate_content([
    "What's in this image?",
    {"mime_type": "image/png", "data": open("screenshot.png", "rb").read()}
])
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for Gemini file path without preprocessing")

    # ========== TRUE POSITIVES - Other Providers ==========

    def test_azure_openai_raw_image(self):
        """Azure OpenAI: Raw image without preprocessing -> REPORT."""
        code = """
from openai import AzureOpenAI
client = AzureOpenAI()
response = client.chat.completions.create(
    model="gpt-4-vision",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Analyze"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for Azure OpenAI raw image")

    def test_ollama_raw_image(self):
        """Ollama: Raw image without preprocessing -> REPORT."""
        code = """
import ollama
response = ollama.chat(
    model="llava",
    messages=[{
        "role": "user",
        "content": "Describe this image",
        "images": [raw_image_bytes]
    }]
)
"""
        # Run the rule and then print debug info
        self.run_rule(code)
        print("DEBUG [test_ollama_raw_image] messages:", self.messages)
        try:
            tree = ast.parse(code)
            if hasattr(generated_rules_R31, "add_parent_info"):
                generated_rules_R31.add_parent_info(tree)
            print("DEBUG [test_ollama_raw_image] AST call funcs and isVisionModelCall results:")
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    try:
                        func_dump = ast.dump(node.func)
                    except Exception:
                        func_dump = "<dump failed>"
                    is_vision = False
                    try:
                        if hasattr(generated_rules_R31, "isVisionModelCall"):
                            is_vision = generated_rules_R31.isVisionModelCall(node)
                    except Exception as e:
                        print("DEBUG isVisionModelCall raised:", e)
                    print("  CALL func:", func_dump, "-> isVisionModelCall:", is_vision)
        except Exception as e:
            print("DEBUG AST parse/inspect error:", e)
        self.assertTrue(self.messages, "Expected a report for Ollama raw image")

    # ========== TRUE NEGATIVES - OpenAI Preprocessed (should NOT report) ==========

    def test_openai_resized_and_cropped_image(self):
        """OpenAI: Image preprocessed with resize and crop -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()

def describe_bug(screenshot_bytes):
    small_image = resize_and_crop(screenshot_bytes, max_side=1024)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Describe the bug"},
                {"type": "input_image", "image": small_image, "detail": "low"}
            ]
        }],
        temperature=0.2
    )
    return response.output[0].content[0].text
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when image is preprocessed with resize")

    def test_openai_explicit_detail_level_low(self):
        """OpenAI: Image with explicit detail level set to low -> NO REPORT."""
        code = """
import openai
resp = openai.ChatCompletion.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Quick overview"},
            {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when detail level is explicitly set to low")

    def test_openai_explicit_detail_level_high(self):
        """OpenAI: Image with explicit detail level set to high -> NO REPORT."""
        code = """
import openai
resp = openai.ChatCompletion.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Fine-grained analysis"},
            {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when detail level is explicitly set")

    def test_openai_cropped_region_of_interest(self):
        """OpenAI: Cropping to region of interest before sending -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()

def analyze_button(screenshot_bytes, button_coords):
    cropped = crop_to_region(screenshot_bytes, button_coords)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Analyze this button"},
                {"type": "input_image", "image": cropped}
            ]
        }]
    )
    return response
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when image is cropped to ROI")

    def test_openai_downscaled_with_max_resolution(self):
        """OpenAI: Downscaling to max resolution -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()

MAX_IMAGE_SIZE = 1024

def process_screenshot(img_bytes):
    resized = downscale_image(img_bytes, max_size=MAX_IMAGE_SIZE)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "What do you see?"},
                {"type": "input_image", "image": resized, "detail": "low"}
            ]
        }]
    )
    return response
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when image is downscaled with budget")

    def test_openai_pil_resize(self):
        """OpenAI: PIL resize before sending -> NO REPORT."""
        code = """
from openai import OpenAI
from PIL import Image
import io

client = OpenAI()
img = Image.open("screenshot.png")
img_resized = img.resize((800, 600))
buffer = io.BytesIO()
img_resized.save(buffer, format="PNG")
img_bytes = buffer.getvalue()

response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Analyze"},
            {"type": "input_image", "image": img_bytes}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when using PIL resize")

    def test_openai_cv2_resize(self):
        """OpenAI: OpenCV resize before sending -> NO REPORT."""
        code = """
from openai import OpenAI
import cv2

client = OpenAI()
img = cv2.imread("screenshot.png")
img_resized = cv2.resize(img, (1024, 768))
_, buffer = cv2.imencode('.png', img_resized)
img_bytes = buffer.tobytes()

response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "What's here?"},
            {"type": "input_image", "image": img_bytes}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when using cv2.resize")

    def test_openai_thumbnail_preprocessing(self):
        """OpenAI: Thumbnail creation before sending -> NO REPORT."""
        code = """
from openai import OpenAI
from PIL import Image

client = OpenAI()
img = Image.open("photo.jpg")
img.thumbnail((512, 512))
response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Describe"},
            {"type": "input_image", "image": img}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when using thumbnail")

    def test_openai_variable_name_suggests_preprocessing(self):
        """OpenAI: Variable name suggesting preprocessing -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()

small_image = get_optimized_image()
response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Analyze"},
            {"type": "input_image", "image": small_image}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when variable name suggests preprocessing")

    def test_openai_image_url_with_preprocessing_function(self):
        """OpenAI: Image URL that goes through preprocessing function -> NO REPORT."""
        code = """
import openai

def preprocess_image_url(url):
    # Fetch, resize, and optimize
    return optimized_url

resp = openai.ChatCompletion.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Analyze"},
            {"type": "image_url", "image_url": {"url": preprocess_image_url(raw_url), "detail": "low"}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when URL goes through preprocessing")

    # ========== TRUE NEGATIVES - Anthropic Preprocessed ==========

    def test_anthropic_resized_image(self):
        """Anthropic: Resized image before sending -> NO REPORT."""
        code = """
import anthropic
client = anthropic.Anthropic()

resized_data = resize_image(raw_data, max_size=1024)
response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Analyze"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": resized_data}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report Anthropic with resized image")

    def test_anthropic_cropped_image(self):
        """Anthropic: Cropped image before sending -> NO REPORT."""
        code = """
from anthropic import Anthropic
client = Anthropic()

cropped_img = crop_to_region(screenshot, coords)
response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=2048,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this region?"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": cropped_img}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report Anthropic with cropped image")

    def test_anthropic_compressed_image(self):
        """Anthropic: Compressed image before sending -> NO REPORT."""
        code = """
import anthropic
client = anthropic.Anthropic()

compressed = compress_image(raw_bytes, quality=70)
response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": compressed}}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report Anthropic with compressed image")

    # ========== TRUE NEGATIVES - Gemini Preprocessed ==========

    def test_gemini_resized_image(self):
        """Gemini: Resized image before sending -> NO REPORT."""
        code = """
import google.generativeai as genai
model = genai.GenerativeModel("gemini-2.0-flash")

small_img = downscale(original_image, max_dimension=1024)
response = model.generate_content([
    "Describe this",
    {"mime_type": "image/png", "data": small_img}
])
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report Gemini with resized image")

    def test_gemini_preprocessed_variable(self):
        """Gemini: Variable with preprocessing name -> NO REPORT."""
        code = """
import google.generativeai as genai
model = genai.GenerativeModel("gemini-pro-vision")

processed_image = preprocess_screenshot(raw_screenshot)
response = model.generate_content([
    "What do you see?",
    {"mime_type": "image/jpeg", "data": processed_image}
])
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report Gemini with preprocessed variable")

    # ========== FALSE POSITIVES TO AVOID ==========

    def test_text_only_no_images(self):
        """Text-only request without images -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()
response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [{"type": "input_text", "text": "Hello, how are you?"}]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Text-only requests should not be flagged")

    def test_non_vision_model(self):
        """Non-vision model call -> NO REPORT."""
        code = """
import openai
resp = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Simple text query"}]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Non-vision models should not be flagged")

    def test_non_llm_image_processing(self):
        """Non-LLM image processing -> NO REPORT."""
        code = """
from PIL import Image
img = Image.open("screenshot.png")
processed = img.resize((800, 600))
processed.save("output.png")
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Non-LLM image processing should not be flagged")

    def test_text_extraction_instead_of_screenshot(self):
        """Extracting text instead of sending screenshot -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()

def analyze_document(doc_image):
    extracted_text = ocr_extract_text(doc_image)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": f"Analyze this text: {extracted_text}"}
            ]
        }]
    )
    return response
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report when text is extracted instead of image")

    def test_database_create_method(self):
        """Database create() method -> NO REPORT."""
        code = """
from myapp import Database
db = Database()
db.users.create(name="John", email="john@example.com")
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Database operations should not be flagged")

    def test_generic_api_client_create(self):
        """Generic API client create() -> NO REPORT."""
        code = """
from myapi import APIClient
client = APIClient()
result = client.resources.create(data={"key": "value"})
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Generic API create should not be flagged")

    # ========== MIXED CASES ==========

    def test_mixed_preprocessed_and_raw(self):
        """One preprocessed call, one raw -> report only raw."""
        code = """
from openai import OpenAI
client = OpenAI()

# Preprocessed (good)
small_img = resize_image(img1, 1024)
r1 = client.responses.create(
    model="gpt-4.1-mini",
    input=[{"role": "user", "content": [
        {"type": "input_text", "text": "A"},
        {"type": "input_image", "image": small_img, "detail": "low"}
    ]}]
)

# Raw (bad)
r2 = client.responses.create(
    model="gpt-4.1-mini",
    input=[{"role": "user", "content": [
        {"type": "input_text", "text": "B"},
        {"type": "input_image", "image": raw_bytes}
    ]}]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 1, "Should report only the raw image call")

    def test_multiple_raw_images_in_one_call(self):
        """Multiple raw images in single call -> REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()
response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Compare all these screenshots"},
            {"type": "input_image", "image": screen1},
            {"type": "input_image", "image": screen2},
            {"type": "input_image", "image": screen3}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Should report multiple raw images without preprocessing")

    # ========== EDGE CASES ==========

    def test_nested_preprocessing_function_call(self):
        """Nested preprocessing function calls -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()

optimized = optimize_image(resize_image(crop_image(raw_img)))
response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Analyze"},
            {"type": "input_image", "image": optimized}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertEqual(len(self.messages), 0, "Should not report nested preprocessing")

    def test_preprocessing_in_separate_function(self):
        """Preprocessing done in separate function -> NO REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()

def prepare_image(raw):
    return resize(raw, 1024)

prepared = prepare_image(screenshot)
response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Check this"},
            {"type": "input_image", "image": prepared}
        ]
    }]
)
"""
        # Run the rule and then print debug info
        self.run_rule(code)
        print("DEBUG [test_preprocessing_in_separate_function] messages:", self.messages)
        try:
            tree = ast.parse(code)
            if hasattr(generated_rules_R31, "add_parent_info"):
                generated_rules_R31.add_parent_info(tree)
            print("DEBUG [test_preprocessing_in_separate_function] Assignments and calls:")
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    print("  ASSIGN:", ast.dump(node, include_attributes=True))
                if isinstance(node, ast.Call):
                    try:
                        func_dump = ast.dump(node.func)
                    except Exception:
                        func_dump = "<dump failed>"
                    print("  CALL func:", func_dump)
                    try:
                        if hasattr(generated_rules_R31, "isVisionModelCall"):
                            print("    isVisionModelCall:", generated_rules_R31.isVisionModelCall(node))
                    except Exception as e:
                        print("    isVisionModelCall raised:", e)
        except Exception as e:
            print("DEBUG AST parse/inspect error:", e)
        self.assertEqual(len(self.messages), 0, "Should not report preprocessing in separate function")

    def test_image_loaded_from_file_no_preprocessing(self):
        """Image loaded from file without preprocessing -> REPORT."""
        code = """
from openai import OpenAI
client = OpenAI()

with open("screenshot.png", "rb") as f:
    img_data = f.read()

response = client.responses.create(
    model="gpt-4.1-mini",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Describe this screenshot"},
            {"type": "input_image", "image": img_data}
        ]
    }]
)
"""
        self.run_rule(code)
        self.assertTrue(self.messages, "Expected a report for image loaded from file without preprocessing")
