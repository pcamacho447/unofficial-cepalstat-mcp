from pathlib import Path
import pytest
from unofficial_cepalstat_mcp.catalog.store import CatalogStore
from unofficial_cepalstat_mcp.dimensions import Dimension, Member
from unofficial_cepalstat_mcp.semantic.registry import SemanticRegistry
from unofficial_cepalstat_mcp.semantic.models import RelationshipType, TemporalAvailabilityStatus


def test_catalog_store_relational_schema(tmp_path: Path):
    db_path = tmp_path / "test_semantic_relational.db"
    store = CatalogStore(db_path=db_path)
    store.init_semantic_tables()

    # Store dimensions and members
    dims = [
        Dimension(
            id=144,
            name="Sexo__ESTANDAR",
            members=[Member(id=265, name="Hombres"), Member(id=266, name="Mujeres")],
        ),
        Dimension(
            id=326,
            name="Área geográfica",
            members=[Member(id=327, name="Nacional"), Member(id=331, name="Rural")],
        ),
    ]
    store.store_indicator_dimensions(3341, dims)
    loaded_dims = store.get_indicator_dimensions(3341)
    assert len(loaded_dims) == 2
    assert loaded_dims[0].id == 144
    assert len(loaded_dims[0].members) == 2
    assert loaded_dims[0].members[1].name == "Mujeres"

    # Store relationship
    store.store_relationship(3341, 3328, "breakdown_of")
    rels = store.get_relationships(3341)
    assert rels.get(3328) == "breakdown_of"

    # Store temporal availability
    store.store_temporal_record(3328, "CHL", 2021, "PERIOD_UNOBSERVED", 2020, 2022)
    temp_rec = store.get_temporal_record(3328, "CHL", 2021)
    assert temp_rec is not None
    assert temp_rec[0] == "PERIOD_UNOBSERVED"
    assert temp_rec[1] == 2020
    assert temp_rec[2] == 2022

    # Query via SemanticRegistry backed by this store
    registry = SemanticRegistry(store=store)
    rel = registry.check_relationship(3341, 3328)
    assert rel == RelationshipType.BREAKDOWN_OF
    status, prev_a, next_a = registry.check_temporal_availability(3328, "CHL", 2021)
    assert status == TemporalAvailabilityStatus.PERIOD_UNOBSERVED
    assert prev_a == 2020
    assert next_a == 2022

    # Query dimensions via SemanticRegistry
    reg_dims = registry.get_dimensions(3341)
    assert len(reg_dims) == 2
    assert reg_dims[0].id == 144
    assert reg_dims[1].name == "Área geográfica"

    # Missing indicator returns empty list or None
    assert store.get_indicator_dimensions(99999) == []
    assert store.get_temporal_record(99999, "CHL", 2021) is None
    assert store.get_relationships(99999) == {}

    # In-memory dictionary fallback tests
    in_mem_dims = [Dimension(id=99, name="Test Dim", members=[Member(id=1, name="M1")])]
    registry_in_mem = SemanticRegistry(
        dimensions={5555: in_mem_dims},
        relationships={(5555, 6666): RelationshipType.ALTERNATIVE_MEASURE},
        temporal_availability={(5555, "ARG", 2020): (TemporalAvailabilityStatus.PERIOD_UNOBSERVED, 2018, 2022)},
    )
    assert registry_in_mem.get_dimensions(5555) == in_mem_dims
    assert registry_in_mem.check_relationship(5555, 6666) == RelationshipType.ALTERNATIVE_MEASURE
    s_in_mem, p_in_mem, n_in_mem = registry_in_mem.check_temporal_availability(5555, "ARG", 2020)
    assert s_in_mem == TemporalAvailabilityStatus.PERIOD_UNOBSERVED
    assert p_in_mem == 2018
    assert n_in_mem == 2022

    # Fallback to static vertical slice indicators
    assert registry.check_relationship(127, 5097) == RelationshipType.BREAKDOWN_OF

