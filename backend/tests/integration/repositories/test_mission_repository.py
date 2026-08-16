from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_session_factory
from app.models import (
    ItemVerdict,
    Mission,
    MissionEventType,
    MissionItem,
    MissionStatus,
    RouteKind,
    RouteStepKind,
)
from app.repositories.missions import (
    DuplicateJoinCodeError,
    ItemVerification,
    LocationUpdate,
    MissionItemSeed,
    MissionRepository,
    MissionSeed,
    SensitiveEventPayloadError,
)
from app.schemas.common import MissionRole
from app.security import MissionJoinCodeVerifier, MissionRoleTokenVerifier
from app.security.tokens import (
    generate_join_code,
    generate_opaque_token,
    hash_opaque_token,
)


@pytest.fixture
def repository(tmp_path):
    database_path = tmp_path / "repository.sqlite3"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    repository = MissionRepository(create_session_factory(engine))
    try:
        yield repository, engine
    finally:
        engine.dispose()


def _create_mission(repository: MissionRepository):
    parent_token = generate_opaque_token()
    child_token = generate_opaque_token()
    join_code = generate_join_code()
    aggregate = repository.create_mission(
        MissionSeed(
            home_lat=37.5665,
            home_lng=126.9780,
            store_lat=37.5651,
            store_lng=126.9895,
            outbound_route={"points": [[126.9780, 37.5665]]},
            return_route={"points": [[126.9895, 37.5651]]},
            parent_token_hash=hash_opaque_token(parent_token),
            join_code=join_code,
            join_code_expires_at=datetime.now(UTC) + timedelta(minutes=30),
        ),
        [MissionItemSeed(name="우유", brand="서울우유", size="1L")],
    )
    return aggregate, parent_token, child_token, join_code


def test_base_metadata_initializes_exactly_three_tables(repository) -> None:
    _, engine = repository

    assert set(inspect(engine).get_table_names()) == {
        "mission_events",
        "mission_items",
        "missions",
    }


def test_mission_aggregate_round_trip_and_updates(repository) -> None:
    mission_repository, _ = repository
    created, _, _, _ = _create_mission(mission_repository)

    loaded = mission_repository.get_aggregate(created.mission.id)

    assert loaded is not None
    assert loaded.mission.status is MissionStatus.WAITING
    assert loaded.mission.current_route_kind is RouteKind.OUTBOUND
    assert loaded.mission.current_step_kind is RouteStepKind.UNKNOWN
    assert [item.name for item in loaded.items] == ["우유"]

    observed_at = datetime.now(UTC)
    updated = mission_repository.update_location(
        created.mission.id,
        LocationUpdate(
            lat=37.5660,
            lng=126.9800,
            observed_at=observed_at,
            accuracy_m=7.5,
            heading_deg=90.0,
            speed_mps=1.2,
            route_kind=RouteKind.OUTBOUND,
            step_index=2,
            step_kind=RouteStepKind.TURN_LEFT,
            progress_m=120.0,
            off_route_streak=1,
            wrong_way_streak=0,
            arrival_streak=0,
        ),
    )

    assert updated.last_location_at == observed_at
    assert updated.last_accuracy_m == 7.5
    assert updated.current_step_index == 2
    assert updated.progress_m == 120.0

    item = loaded.items[0]
    verified = mission_repository.update_item_verification(
        created.mission.id,
        item.id,
        ItemVerification(
            verdict=ItemVerdict.MATCH,
            detected_label="서울우유 1L",
            description="요청한 상품과 일치",
            verified_at=observed_at,
        ),
    )

    assert verified is not None
    assert verified.last_verdict is ItemVerdict.MATCH


def test_plaintext_credentials_are_never_persisted(repository) -> None:
    mission_repository, engine = repository
    aggregate, parent_token, child_token, join_code = _create_mission(mission_repository)

    with Session(engine) as session:
        mission = session.scalar(select(Mission).where(Mission.id == aggregate.mission.id))

    assert mission is not None
    stored_values = {
        mission.parent_token_hash,
        mission.child_token_hash,
        mission.join_code_hash,
    }
    assert parent_token not in stored_values
    assert child_token not in stored_values
    assert join_code not in stored_values
    mission_columns = {column["name"] for column in inspect(engine).get_columns("missions")}
    assert "parent_token" not in mission_columns
    assert "child_token" not in mission_columns
    assert "join_code" not in mission_columns
    assert mission.parent_token_hash.startswith("sha256$")
    assert mission.join_code_hash is not None
    assert mission.join_code_hash.startswith("pbkdf2_sha256$")


def test_repository_rejects_plaintext_parent_token_hash(repository) -> None:
    mission_repository, engine = repository

    with pytest.raises(ValueError):
        mission_repository.create_mission(
            MissionSeed(
                home_lat=37.55,
                home_lng=126.97,
                store_lat=37.56,
                store_lng=126.98,
                outbound_route={"points": []},
                return_route={"points": []},
                parent_token_hash=generate_opaque_token(),
                join_code="135790",
                join_code_expires_at=datetime.now(UTC) + timedelta(minutes=30),
            ),
            [],
        )

    with Session(engine) as session:
        assert session.scalars(select(Mission)).all() == []


def test_repository_rejects_plaintext_child_token_hash_without_consuming_code(
    repository,
) -> None:
    mission_repository, _ = repository
    aggregate, _, child_token, join_code = _create_mission(mission_repository)

    with pytest.raises(ValueError):
        mission_repository.consume_join_code(
            aggregate.mission.id,
            child_token_hash=child_token,
        )

    mission = mission_repository.get_mission(aggregate.mission.id)
    assert mission is not None
    assert mission.status is MissionStatus.WAITING
    assert mission.child_token_hash is None
    assert MissionJoinCodeVerifier(mission_repository).find_mission_id(join_code) == mission.id


def test_role_token_verifier_separates_parent_and_child(repository) -> None:
    mission_repository, _ = repository
    aggregate, parent_token, child_token, _ = _create_mission(mission_repository)
    verifier = MissionRoleTokenVerifier(mission_repository)

    parent = verifier.verify(parent_token, MissionRole.PARENT)
    assert verifier.verify(child_token, MissionRole.CHILD) is None
    assert mission_repository.consume_join_code(
        aggregate.mission.id,
        child_token_hash=hash_opaque_token(child_token),
    )
    child = verifier.verify(child_token, MissionRole.CHILD)

    assert parent is not None
    assert parent.mission_id == aggregate.mission.id
    assert parent.role is MissionRole.PARENT
    assert child is not None
    assert child.mission_id == aggregate.mission.id
    assert child.role is MissionRole.CHILD
    assert verifier.verify(parent_token, MissionRole.CHILD) is None
    assert verifier.verify("not-a-real-token", MissionRole.PARENT) is None


def test_join_code_is_resolved_then_consumed_once(repository) -> None:
    mission_repository, _ = repository
    aggregate, _, child_token, join_code = _create_mission(mission_repository)
    verifier = MissionJoinCodeVerifier(mission_repository)

    assert verifier.find_mission_id(join_code) == aggregate.mission.id
    assert mission_repository.consume_join_code(
        aggregate.mission.id,
        child_token_hash=hash_opaque_token(child_token),
    )
    assert verifier.find_mission_id(join_code) is None
    assert not mission_repository.consume_join_code(
        aggregate.mission.id,
        child_token_hash=hash_opaque_token(generate_opaque_token()),
    )

    mission = mission_repository.get_mission(aggregate.mission.id)
    assert mission is not None
    assert mission.status is MissionStatus.GOING
    assert mission.join_code_hash is None
    assert mission.join_code_expires_at is None


def test_active_join_code_collision_is_rejected(repository) -> None:
    mission_repository, _ = repository
    _, _, _, join_code = _create_mission(mission_repository)

    with pytest.raises(DuplicateJoinCodeError):
        mission_repository.create_mission(
            MissionSeed(
                home_lat=37.55,
                home_lng=126.97,
                store_lat=37.56,
                store_lng=126.98,
                outbound_route={"points": []},
                return_route={"points": []},
                parent_token_hash=hash_opaque_token(generate_opaque_token()),
                join_code=join_code,
                join_code_expires_at=datetime.now(UTC) + timedelta(minutes=30),
            ),
            [],
        )


def test_concurrent_join_code_collision_has_one_winner(repository) -> None:
    mission_repository, _ = repository
    join_code = "246810"

    def create(parent_token: str) -> str:
        aggregate = mission_repository.create_mission(
            MissionSeed(
                home_lat=37.55,
                home_lng=126.97,
                store_lat=37.56,
                store_lng=126.98,
                outbound_route={"points": []},
                return_route={"points": []},
                parent_token_hash=hash_opaque_token(parent_token),
                join_code=join_code,
                join_code_expires_at=datetime.now(UTC) + timedelta(minutes=30),
            ),
            [],
        )
        return aggregate.mission.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create, generate_opaque_token()) for _ in range(2)]

    outcomes: list[str] = []
    for future in futures:
        try:
            outcomes.append(future.result())
        except DuplicateJoinCodeError:
            outcomes.append("duplicate")

    assert len([outcome for outcome in outcomes if outcome != "duplicate"]) == 1
    assert outcomes.count("duplicate") == 1


def test_expired_join_code_can_be_reused(repository) -> None:
    mission_repository, engine = repository
    aggregate, _, _, join_code = _create_mission(mission_repository)
    with Session(engine) as session, session.begin():
        mission = session.get(Mission, aggregate.mission.id)
        assert mission is not None
        mission.join_code_expires_at = datetime.now(UTC) - timedelta(seconds=1)

    replacement = mission_repository.create_mission(
        MissionSeed(
            home_lat=37.55,
            home_lng=126.97,
            store_lat=37.56,
            store_lng=126.98,
            outbound_route={"points": []},
            return_route={"points": []},
            parent_token_hash=hash_opaque_token(generate_opaque_token()),
            join_code=join_code,
            join_code_expires_at=datetime.now(UTC) + timedelta(minutes=30),
        ),
        [],
    )

    assert replacement.mission.id != aggregate.mission.id


def test_events_after_cursor_are_returned_in_ascending_order(repository) -> None:
    mission_repository, _ = repository
    aggregate, _, _, _ = _create_mission(mission_repository)
    first = mission_repository.append_event(
        aggregate.mission.id,
        MissionEventType.STATUS_CHANGED,
        {"status": MissionStatus.GOING.value},
    )
    second = mission_repository.append_event(
        aggregate.mission.id,
        MissionEventType.ROAD_HAZARD,
        {"result": "STOP"},
    )
    third = mission_repository.append_event(
        aggregate.mission.id,
        MissionEventType.ITEM_VERIFIED,
        {"result": ItemVerdict.MATCH.value},
    )

    events = mission_repository.list_events(aggregate.mission.id, after_event_id=first.id)

    assert [event.id for event in events] == [second.id, third.id]
    assert [event.id for event in events] == sorted(event.id for event in events)


def test_event_payload_rejects_raw_image_material(repository) -> None:
    mission_repository, _ = repository
    aggregate, _, _, _ = _create_mission(mission_repository)

    with pytest.raises(SensitiveEventPayloadError):
        mission_repository.append_event(
            aggregate.mission.id,
            MissionEventType.ROAD_HAZARD,
            {"frame_bytes": b"not-an-image-fixture"},
        )

    with pytest.raises(SensitiveEventPayloadError):
        mission_repository.append_event(
            aggregate.mission.id,
            MissionEventType.ROAD_HAZARD,
            {"imageBase64": "data:image/jpeg;base64,AAAA"},
        )

    with pytest.raises(SensitiveEventPayloadError):
        mission_repository.append_event(
            aggregate.mission.id,
            MissionEventType.ROAD_HAZARD,
            {"content": "/9j/4AAQSkZJRgABAQAAAQABAAD"},
        )


def test_event_payload_allows_safe_image_and_frame_metadata(repository) -> None:
    mission_repository, _ = repository
    aggregate, _, _, _ = _create_mission(mission_repository)

    event = mission_repository.append_event(
        aggregate.mission.id,
        MissionEventType.ROAD_HAZARD,
        {
            "image_id": "normalized-image-1",
            "frame_index": 3,
            "image_sha256": "a" * 64,
        },
    )

    assert event.payload == {
        "image_id": "normalized-image-1",
        "frame_index": 3,
        "image_sha256": "a" * 64,
    }


def test_road_vision_lease_is_atomic_expires_and_releases(repository) -> None:
    mission_repository, _ = repository
    aggregate, _, _, _ = _create_mission(mission_repository)
    mission_id = aggregate.mission.id
    now = datetime.now(UTC)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: mission_repository.acquire_road_vision_lease(mission_id, now=now),
                range(2),
            )
        )

    assert sorted(results) == [False, True]
    assert not mission_repository.acquire_road_vision_lease(
        mission_id, now=now + timedelta(seconds=9)
    )
    assert mission_repository.acquire_road_vision_lease(mission_id, now=now + timedelta(seconds=11))
    assert not mission_repository.release_road_vision_lease(
        mission_id,
        expected_lease_until=now + timedelta(seconds=10),
    )
    assert not mission_repository.acquire_road_vision_lease(
        mission_id, now=now + timedelta(seconds=12)
    )
    assert mission_repository.release_road_vision_lease(
        mission_id,
        expected_lease_until=now + timedelta(seconds=21),
    )
    assert mission_repository.acquire_road_vision_lease(mission_id, now=now + timedelta(seconds=12))


def test_delete_mission_removes_aggregate(repository) -> None:
    mission_repository, engine = repository
    aggregate, _, _, _ = _create_mission(mission_repository)

    assert mission_repository.delete_mission(aggregate.mission.id)
    assert mission_repository.get_aggregate(aggregate.mission.id) is None

    with Session(engine) as session:
        assert session.scalars(select(MissionItem)).all() == []
