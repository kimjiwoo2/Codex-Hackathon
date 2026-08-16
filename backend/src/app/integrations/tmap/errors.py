from app.core.errors import AppError


class TmapUnavailable(AppError):
    """Normalize transport and invalid-route failures without leaking provider details."""

    def __init__(self) -> None:
        super().__init__(
            code="TMAP_UNAVAILABLE",
            message="보행 경로를 불러오지 못했습니다.",
            status_code=503,
        )
