"""用户行政区划（民政部 adcode）。开发期老账号可无 region。"""
import re

from pydantic import BaseModel, Field, field_validator

_ADCODE = re.compile(r"^\d{6}$")


class UserRegion(BaseModel):
    province_code: str = Field(..., description="省份 adcode")
    city_code: str = Field(...)
    district_code: str = Field(...)
    province_name: str = ""
    city_name: str = ""
    district_name: str = ""

    @field_validator("province_code", "city_code", "district_code")
    @classmethod
    def validate_adcode(cls, v: str) -> str:
        s = (v or "").strip()
        if not _ADCODE.match(s):
            raise ValueError("行政区编码须为 6 位数字 adcode")
        return s

    def mongo_dict(self) -> dict[str, str]:
        return self.model_dump()
