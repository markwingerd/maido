class MaidoError(Exception):
    category = "maido_error"

    def __init__(self, message, **details):
        super().__init__(message)
        self.message = message
        self.details = details

    def to_dict(self):
        data = {
            "category": self.category,
            "message": self.message,
        }
        if self.details:
            data["details"] = self.details
        return data


class ArchiveError(MaidoError):
    category = "archive_error"


class ManifestParseError(MaidoError):
    category = "manifest_parse_error"


class ManifestValidationError(MaidoError):
    category = "manifest_validation_error"


class VideoProbeError(MaidoError):
    category = "video_probe_error"


class CropConflictError(MaidoError):
    category = "crop_conflict_error"
