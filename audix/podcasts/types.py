from typing import Annotated

from pydantic import AfterValidator


def validate_image_url(v: str) -> str:
    valid_extensions = (".jpg", ".jpeg", ".png", ".webp",)
    clean_url = v.split("?")[0].lower()
    
    if not clean_url.endswith(valid_extensions):
        raise ValueError(
            "A imagem deve estar nos formatos: .jpg, .jpeg, .png ou .webp"
        )
    return v

ValidImage = Annotated[str, AfterValidator(validate_image_url)]
