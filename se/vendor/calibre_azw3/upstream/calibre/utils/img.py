"""
Provide the image operations used by calibre's AZW3 writer through Pillow.
"""

from io import BytesIO

from PIL import Image


class ImageWrapper:
	"""
	Wrap a Pillow image with the dimension methods expected by calibre.
	"""

	def __init__(self, image: Image.Image) -> None:
		"""
		Store the wrapped Pillow image.
		"""

		self.image = image

	def width(self) -> int:
		"""
		Return the image width.
		"""

		return self.image.width

	def height(self) -> int:
		"""
		Return the image height.
		"""

		return self.image.height

def image_from_data(data: bytes) -> ImageWrapper:
	"""
	Decode image data into a wrapped Pillow image.
	"""

	return ImageWrapper(Image.open(BytesIO(data)).copy())

def image_to_data(image: ImageWrapper | Image.Image, compression_quality: int = 95, fmt: str = "JPEG", png_compression_level: int = 9, jpeg_optimized: bool = True, jpeg_progressive: bool = False) -> bytes:
	"""
	Encode an image using the requested format and compression settings.
	"""

	source = image.image if isinstance(image, ImageWrapper) else image
	if fmt.upper() in {"JPEG", "JPG"} and source.mode not in {"RGB", "L"}:
		background = Image.new("RGB", source.size, "white")
		if "A" in source.getbands():
			background.paste(source, mask=source.getchannel("A"))
		else:
			background.paste(source)

		source = background

	output = BytesIO()
	source.save(output, format=fmt, quality=compression_quality, optimize=jpeg_optimized, progressive=jpeg_progressive, compress_level=png_compression_level)

	return output.getvalue()

def resize_image(image: ImageWrapper | Image.Image, width: int, height: int) -> ImageWrapper:
	"""
	Resize an image to the exact requested dimensions.
	"""

	source = image.image if isinstance(image, ImageWrapper) else image
	return ImageWrapper(source.resize((int(width), int(height)), Image.Resampling.LANCZOS))

def scale_image(data: bytes, width: int = 60, height: int = 80, compression_quality: int = 70, as_png: bool = False, preserve_aspect_ratio: bool = True) -> tuple[int, int, bytes]:
	"""
	Scale encoded image data and return its dimensions and encoded result.
	"""

	image = Image.open(BytesIO(data)).copy()
	if preserve_aspect_ratio:
		image.thumbnail((int(width), int(height)), Image.Resampling.LANCZOS)
	else:
		image = image.resize((int(width), int(height)), Image.Resampling.LANCZOS)

	fmt = "PNG" if as_png else "JPEG"
	return image.width, image.height, image_to_data(image, compression_quality=compression_quality, fmt=fmt)

def save_cover_data_to(data: bytes, path: str | None = None, **kwargs: object) -> bytes:
	"""
	Convert cover data to an opaque encoded image and optionally save it.
	"""

	compression_quality = int(kwargs.get("compression_quality", 90))
	fmt = str(kwargs.get("data_fmt", "jpeg"))
	source = Image.open(BytesIO(data))

	if fmt.lower() in {"jpeg", "jpg"} and source.format == "JPEG" and "A" not in source.getbands():
		result = data
	else:
		result = image_to_data(ImageWrapper(source.copy()), compression_quality=compression_quality, fmt=fmt)

	if path is not None:
		with open(path, "wb") as file:
			file.write(result)

	return result

def png_data_to_gif_data(data: bytes) -> bytes:
	"""
	Convert PNG data to GIF data.
	"""

	image = Image.open(BytesIO(data))
	output = BytesIO()
	image.save(output, format="GIF")

	return output.getvalue()
