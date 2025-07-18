"""
Service for extracting dominant colors from logos
"""
import io
import logging
from typing import List, Tuple, Optional
from colorthief import ColorThief
import requests
from PIL import Image

logger = logging.getLogger(__name__)


class ColorExtractionService:
    """Service for extracting colors from images"""
    
    @staticmethod
    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex color string"""
        return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
    
    @staticmethod
    def is_color_too_light(rgb: Tuple[int, int, int], threshold: int = 240) -> bool:
        """Check if a color is too light (close to white)"""
        return all(c > threshold for c in rgb)
    
    @staticmethod
    def is_color_too_dark(rgb: Tuple[int, int, int], threshold: int = 30) -> bool:
        """Check if a color is too dark (close to black)"""
        return all(c < threshold for c in rgb)
    
    @staticmethod
    def is_grayscale(rgb: Tuple[int, int, int], tolerance: int = 20) -> bool:
        """Check if a color is grayscale"""
        return max(rgb) - min(rgb) < tolerance
    
    @classmethod
    def extract_colors_from_url(cls, image_url: str) -> Optional[dict]:
        """
        Extract dominant colors from an image URL
        
        Returns:
            dict with primary_color, secondary_color, and accent_color as hex strings
        """
        try:
            # Download the image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Open image with PIL
            image = Image.open(io.BytesIO(response.content))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                if image.mode == 'RGBA':
                    # Create a white background
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
                    image = background
                else:
                    image = image.convert('RGB')
            
            # Save to BytesIO for ColorThief
            img_io = io.BytesIO()
            image.save(img_io, format='PNG')
            img_io.seek(0)
            
            # Extract colors
            color_thief = ColorThief(img_io)
            
            # Get the dominant color
            dominant_color = color_thief.get_color(quality=1)
            
            # Get a palette of colors
            palette = color_thief.get_palette(color_count=10, quality=1)
            
            # Filter out colors that are too light, too dark, or grayscale
            filtered_colors = []
            for color in palette:
                if (not cls.is_color_too_light(color) and 
                    not cls.is_color_too_dark(color) and 
                    not cls.is_grayscale(color)):
                    filtered_colors.append(color)
            
            # If we don't have enough filtered colors, use the original palette
            if len(filtered_colors) < 3:
                filtered_colors = palette
            
            # Assign colors
            colors = {
                'primary_color': cls.rgb_to_hex(dominant_color),
                'secondary_color': None,
                'accent_color': None
            }
            
            # Try to find distinct colors for secondary and accent
            if len(filtered_colors) >= 2:
                colors['secondary_color'] = cls.rgb_to_hex(filtered_colors[1])
            
            if len(filtered_colors) >= 3:
                colors['accent_color'] = cls.rgb_to_hex(filtered_colors[2])
            elif len(filtered_colors) >= 2:
                # If we only have 2 colors, make accent slightly different
                # by adjusting the brightness of the secondary color
                secondary_rgb = filtered_colors[1]
                accent_rgb = tuple(min(255, int(c * 1.2)) for c in secondary_rgb)
                colors['accent_color'] = cls.rgb_to_hex(accent_rgb)
            
            logger.info(f"Extracted colors from {image_url}: {colors}")
            return colors
            
        except Exception as e:
            logger.error(f"Failed to extract colors from {image_url}: {str(e)}")
            return None
    
    @classmethod
    def extract_colors_from_svg(cls, svg_url: str) -> Optional[dict]:
        """
        Extract colors from SVG by parsing the SVG content
        This is a simplified version that looks for fill and stroke colors
        """
        try:
            import re
            
            response = requests.get(svg_url, timeout=10)
            response.raise_for_status()
            
            svg_content = response.text
            
            # Find all hex colors in the SVG
            hex_pattern = r'#([0-9A-Fa-f]{6})'
            colors = re.findall(hex_pattern, svg_content)
            
            # Find rgb colors
            rgb_pattern = r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)'
            rgb_colors = re.findall(rgb_pattern, svg_content)
            
            # Convert rgb to hex and add to list
            for rgb in rgb_colors:
                hex_color = cls.rgb_to_hex((int(rgb[0]), int(rgb[1]), int(rgb[2])))
                colors.append(hex_color[1:])  # Remove # for consistency
            
            # Make colors unique and filter out white/black
            unique_colors = []
            seen = set()
            
            for color in colors:
                color = color.lower()
                if color not in seen and color != 'ffffff' and color != '000000':
                    seen.add(color)
                    rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
                    if not cls.is_grayscale(rgb):
                        unique_colors.append('#' + color)
            
            if not unique_colors:
                logger.warning(f"No suitable colors found in SVG {svg_url}")
                return None
            
            # Assign colors
            result = {
                'primary_color': unique_colors[0] if len(unique_colors) > 0 else None,
                'secondary_color': unique_colors[1] if len(unique_colors) > 1 else None,
                'accent_color': unique_colors[2] if len(unique_colors) > 2 else None
            }
            
            logger.info(f"Extracted colors from SVG {svg_url}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract colors from SVG {svg_url}: {str(e)}")
            return None