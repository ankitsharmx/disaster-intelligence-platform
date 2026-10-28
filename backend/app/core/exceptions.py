from typing import Any, Optional, Dict


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "BAD_REQUEST",
        details: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class EntityNotFoundException(AppException):
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with id '{entity_id}' not found",
            status_code=404,
            error_code="NOT_FOUND",
        )


class PermissionDeniedException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
        )


class DistrictAccessDeniedException(PermissionDeniedException):
    def __init__(self, officer_district_id: Optional[int], requested_district_id: Any):
        super().__init__(
            message=(
                f"Access Denied: Officer jurisdiction is limited to district id {officer_district_id}. "
                f"Cannot access or modify records for district {requested_district_id}."
            )
        )


class InvalidOperationException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_OPERATION",
            details=details,
        )


class FileValidationException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_FILE_UPLOAD",
        )


class ConflictException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
        )
