"""Typed IEEE 123-bus OpenDSS adapter for SC-CMPO public benchmarks.

The published feeder files define line impedances through linecodes but do not
publish explicit line ampacity fields such as ``NormalAmps``. This adapter
retains ``normal_amps=None`` for every line rather than inventing ratings.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from cmpo.upgrade_planning import (
    PublicContingency,
    PublicEdge,
    PublicGridData,
    PublicNode,
    UpgradePatch,
    select_upgrade_patches,
    sha256_file,
)


@dataclass(frozen=True)
class PublicGridDataWithMetadata(PublicGridData):
    """PublicGridData with adapter-local metadata."""

    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class BusPhaseConnection:
    """One OpenDSS bus reference with explicit phase terminals."""

    bus_id: str
    phases: tuple[str, ...]
    raw_bus: str


@dataclass(frozen=True)
class IEEE123Bus:
    """One compiled feeder bus with published phase connectivity."""

    bus_id: str
    phases: tuple[str, ...]
    source_record: str


@dataclass(frozen=True)
class IEEE123LineCode:
    """Published OpenDSS linecode impedance/capacitance data."""

    code_id: str
    phase_count: int
    units: str | None
    resistance_matrix: tuple[tuple[float, ...], ...]
    reactance_matrix: tuple[tuple[float, ...], ...]
    capacitance_matrix: tuple[tuple[float, ...], ...]
    source_record: str


@dataclass(frozen=True)
class IEEE123Line:
    """One feeder line or switch."""

    name: str
    from_bus: BusPhaseConnection
    to_bus: BusPhaseConnection
    phases: tuple[str, ...]
    length: float | None
    units: str | None
    linecode_id: str | None
    is_switch: bool
    enabled: bool
    in_service: bool
    normal_amps: float | None
    resistance_matrix: tuple[tuple[float, ...], ...] | None
    reactance_matrix: tuple[tuple[float, ...], ...] | None
    capacitance_matrix: tuple[tuple[float, ...], ...] | None
    source_record: str


@dataclass(frozen=True)
class IEEE123Load:
    """One published feeder load."""

    name: str
    bus: BusPhaseConnection
    declared_phase_count: int
    connection: str
    model: int | None
    nominal_kv: float | None
    active_power_kw: float
    reactive_power_kvar: float
    source_record: str


@dataclass(frozen=True)
class IEEE123TransformerWinding:
    """One transformer winding after LIKE resolution."""

    winding: int
    bus: BusPhaseConnection
    connection: str | None
    nominal_kv: float | None
    rated_kva: float | None
    resistance_percent: float | None


@dataclass(frozen=True)
class IEEE123Transformer:
    """One transformer, including regulator transformers."""

    name: str
    phases: tuple[str, ...]
    windings: tuple[IEEE123TransformerWinding, ...]
    bank: str | None
    xhl_percent: float | None
    load_loss_percent: float | None
    like: str | None
    source_record: str


@dataclass(frozen=True)
class IEEE123Regulator:
    """One OpenDSS regcontrol definition with LIKE resolution."""

    name: str
    transformer_name: str
    winding: int | None
    voltage_regulation: float | None
    band: float | None
    potential_transformer_ratio: float | None
    current_transformer_primary: float | None
    resistance_setting: float | None
    reactance_setting: float | None
    like: str | None
    source_record: str


@dataclass(frozen=True)
class IEEE123Capacitor:
    """One published feeder capacitor."""

    name: str
    bus: BusPhaseConnection
    phase_count: int
    reactive_power_kvar: float
    nominal_kv: float | None
    source_record: str


@dataclass(frozen=True)
class IEEE123SCMPOCase:
    """Parsed IEEE 123-bus feeder plus its PublicGridData projection."""

    benchmark: str
    buses: tuple[IEEE123Bus, ...]
    lines: tuple[IEEE123Line, ...]
    loads: tuple[IEEE123Load, ...]
    transformers: tuple[IEEE123Transformer, ...]
    regulators: tuple[IEEE123Regulator, ...]
    capacitors: tuple[IEEE123Capacitor, ...]
    line_codes: tuple[IEEE123LineCode, ...]
    grid: PublicGridDataWithMetadata
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class _DSSCommand:
    """One normalized OpenDSS command with provenance."""

    kind: str
    name: str
    text: str
    source_path: Path
    line_number: int


def _strip_comment(raw_line: str) -> str:
    return raw_line.split("!", 1)[0].strip()


def _scan_assignment_items(text: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    index = 0
    size = len(text)
    while index < size:
        while index < size and text[index].isspace():
            index += 1
        if index >= size:
            break
        key_start = index
        while index < size and not text[index].isspace() and text[index] != "=":
            index += 1
        key = text[key_start:index]
        while index < size and text[index].isspace():
            index += 1
        if index >= size or text[index] != "=":
            while index < size and not text[index].isspace():
                index += 1
            continue
        index += 1
        while index < size and text[index].isspace():
            index += 1
        if index >= size:
            items.append((key.lower(), ""))
            break
        opener = text[index]
        if opener in "[(":
            closer = "]" if opener == "[" else ")"
            depth = 1
            value_start = index
            index += 1
            while index < size and depth > 0:
                if text[index] == opener:
                    depth += 1
                elif text[index] == closer:
                    depth -= 1
                index += 1
            value = text[value_start:index].strip()
        else:
            value_start = index
            while index < size and not text[index].isspace():
                index += 1
            value = text[value_start:index].strip()
        items.append((key.lower(), value))
    return items


def _items_to_last_map(items: Sequence[tuple[str, str]]) -> dict[str, str]:
    return {key: value for key, value in items}


def _split_array(raw: str) -> tuple[str, ...]:
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    elif text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    return tuple(token for token in re.split(r"[\s,]+", text.strip()) if token)


def _parse_float(raw: str | None) -> float | None:
    if raw is None or raw == "":
        return None
    return float(raw)


def _parse_int(raw: str | None) -> int | None:
    if raw is None or raw == "":
        return None
    return int(float(raw))


def _parse_matrix(raw: str | None, phase_count: int) -> tuple[tuple[float, ...], ...]:
    if raw is None:
        raise ValueError("linecode matrix is missing")
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    elif text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    rows = [segment.strip() for segment in text.split("|")]
    values_by_row = [
        [float(token) for token in re.split(r"[\s,]+", row.strip()) if token]
        for row in rows
        if row.strip()
    ]
    if len(values_by_row) != phase_count:
        raise ValueError(f"expected {phase_count} matrix rows, found {len(values_by_row)}")
    matrix = [[0.0 for _ in range(phase_count)] for _ in range(phase_count)]
    for row_index, row_values in enumerate(values_by_row):
        if len(row_values) != row_index + 1:
            raise ValueError(
                f"expected {row_index + 1} lower-triangular values in row {row_index + 1}, found {len(row_values)}"
            )
        for column_index, value in enumerate(row_values):
            matrix[row_index][column_index] = value
            matrix[column_index][row_index] = value
    return tuple(tuple(row) for row in matrix)


def _default_phase_labels(phase_count: int) -> tuple[str, ...]:
    return tuple(str(index) for index in range(1, phase_count + 1))


def _parse_bus(raw_bus: str, *, fallback_phase_count: int | None = None) -> BusPhaseConnection:
    text = raw_bus.strip()
    if not text:
        return BusPhaseConnection(bus_id="", phases=(), raw_bus=raw_bus)
    parts = [part for part in text.split(".") if part]
    bus_id = parts[0]
    phase_parts = tuple(parts[1:]) if len(parts) > 1 else ()
    if not phase_parts and fallback_phase_count is not None and fallback_phase_count > 0:
        phase_parts = _default_phase_labels(fallback_phase_count)
    return BusPhaseConnection(bus_id=bus_id, phases=phase_parts, raw_bus=raw_bus)


def _yes_no(raw: str | None, *, default: bool = True) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() not in {"no", "false", "0"}


def _command_header(raw_command: str, source_path: Path, line_number: int) -> _DSSCommand | None:
    match = re.match(
        r"^new\s+(?:(?P<kind>[A-Za-z_][\w]*)\.(?P<name>[^\s]+)|object=(?P<object_kind>[^.\s]+)\.(?P<object_name>[^\s]+))\s*(?P<body>.*)$",
        raw_command,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    kind = (match.group("kind") or match.group("object_kind") or "").lower()
    name = match.group("name") or match.group("object_name") or ""
    return _DSSCommand(
        kind=kind,
        name=name,
        text=match.group("body").strip(),
        source_path=source_path,
        line_number=line_number,
    )


def _resolve_redirect(base_path: Path, command: str) -> Path | None:
    match = re.match(r"^redirect\s+(.+)$", command, flags=re.IGNORECASE)
    if match is None:
        return None
    target = match.group(1).strip().strip('"').strip("'")
    return (base_path.parent / target).resolve()


def _collect_commands(path: Path) -> tuple[list[_DSSCommand], tuple[Path, ...]]:
    commands: list[_DSSCommand] = []
    parsed_files: list[Path] = []
    seen_files: set[Path] = set()

    def visit(current_path: Path) -> None:
        resolved = current_path.resolve()
        if resolved in seen_files:
            return
        seen_files.add(resolved)
        parsed_files.append(resolved)
        current_command = ""
        current_line_number = 0
        for line_number, raw_line in enumerate(
            resolved.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            line = _strip_comment(raw_line)
            if not line:
                continue
            if line.startswith("~"):
                if current_command:
                    current_command = f"{current_command} {line[1:].strip()}"
                continue
            if current_command:
                redirect_target = _resolve_redirect(resolved, current_command)
                if redirect_target is not None:
                    visit(redirect_target)
                else:
                    header = _command_header(current_command, resolved, current_line_number)
                    if header is not None:
                        commands.append(header)
            current_command = line
            current_line_number = line_number
        if current_command:
            redirect_target = _resolve_redirect(resolved, current_command)
            if redirect_target is not None:
                visit(redirect_target)
            else:
                header = _command_header(current_command, resolved, current_line_number)
                if header is not None:
                    commands.append(header)

    visit(path)
    return commands, tuple(parsed_files)


def _source_record(command: _DSSCommand) -> str:
    return f"{command.source_path.name} line={command.line_number}: {command.kind}.{command.name}"


def _parse_linecode(command: _DSSCommand) -> IEEE123LineCode:
    items = _scan_assignment_items(command.text)
    properties = _items_to_last_map(items)
    phase_count = _parse_int(properties.get("nphases")) or 3
    return IEEE123LineCode(
        code_id=command.name,
        phase_count=phase_count,
        units=properties.get("units"),
        resistance_matrix=_parse_matrix(properties.get("rmatrix"), phase_count),
        reactance_matrix=_parse_matrix(properties.get("xmatrix"), phase_count),
        capacitance_matrix=_parse_matrix(properties.get("cmatrix"), phase_count),
        source_record=_source_record(command),
    )


def _parse_line(command: _DSSCommand, linecodes: Mapping[str, IEEE123LineCode]) -> IEEE123Line:
    items = _scan_assignment_items(command.text)
    properties = _items_to_last_map(items)
    linecode_id = properties.get("linecode")
    phase_count = _parse_int(properties.get("phases"))
    referenced_linecode = linecodes.get(linecode_id.lower()) if linecode_id is not None else None
    if phase_count is None and referenced_linecode is not None:
        phase_count = referenced_linecode.phase_count
    if phase_count is None:
        phase_count = 3
    from_bus = _parse_bus(properties.get("bus1", ""), fallback_phase_count=phase_count)
    to_bus = _parse_bus(properties.get("bus2", ""), fallback_phase_count=phase_count)
    phases = from_bus.phases or to_bus.phases or _default_phase_labels(phase_count)
    is_switch = _yes_no(properties.get("switch"), default=False)
    enabled = _yes_no(properties.get("enabled"), default=True)
    in_service = enabled and not to_bus.bus_id.lower().endswith("_open")
    return IEEE123Line(
        name=command.name,
        from_bus=from_bus,
        to_bus=to_bus,
        phases=phases,
        length=_parse_float(properties.get("length")),
        units=properties.get("units") or (referenced_linecode.units if referenced_linecode is not None else None),
        linecode_id=linecode_id,
        is_switch=is_switch,
        enabled=enabled,
        in_service=in_service,
        normal_amps=None,
        resistance_matrix=None if is_switch or referenced_linecode is None else referenced_linecode.resistance_matrix,
        reactance_matrix=None if is_switch or referenced_linecode is None else referenced_linecode.reactance_matrix,
        capacitance_matrix=None if is_switch or referenced_linecode is None else referenced_linecode.capacitance_matrix,
        source_record=_source_record(command),
    )


def _transformer_windings_from_arrays(
    properties: Mapping[str, str],
    inherited: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    windings = [dict(record) for record in inherited]
    count = _parse_int(properties.get("windings")) or max(len(windings), len(_split_array(properties.get("buses", ""))), 0)
    while len(windings) < count:
        windings.append({})
    buses = _split_array(properties.get("buses", ""))
    if buses:
        for index, value in enumerate(buses):
            windings[index]["bus"] = value
    conns = _split_array(properties.get("conns", ""))
    if conns:
        for index, value in enumerate(conns):
            windings[index]["conn"] = value
    kvs = _split_array(properties.get("kvs", ""))
    if kvs:
        for index, value in enumerate(kvs):
            windings[index]["kv"] = value
    kvas = _split_array(properties.get("kvas", ""))
    if kvas:
        for index, value in enumerate(kvas):
            windings[index]["kva"] = value
    return windings


def _parse_transformer(
    command: _DSSCommand,
    prior_transformers: Mapping[str, IEEE123Transformer],
) -> IEEE123Transformer:
    items = _scan_assignment_items(command.text)
    properties = _items_to_last_map(items)
    like = properties.get("like")
    inherited = prior_transformers.get(like.lower()) if like is not None else None
    inherited_windings: Sequence[dict[str, Any]] = []
    inherited_phase_count: int | None = None
    inherited_bank: str | None = None
    inherited_xhl: float | None = None
    inherited_load_loss: float | None = None
    if inherited is not None:
        inherited_windings = [
            {
                "bus": winding.bus.raw_bus,
                "conn": winding.connection,
                "kv": winding.nominal_kv,
                "kva": winding.rated_kva,
                "%r": winding.resistance_percent,
            }
            for winding in inherited.windings
        ]
        inherited_phase_count = len(inherited.phases)
        inherited_bank = inherited.bank
        inherited_xhl = inherited.xhl_percent
        inherited_load_loss = inherited.load_loss_percent
    windings = _transformer_windings_from_arrays(properties, inherited_windings)
    active_winding: int | None = None
    for key, value in items:
        if key in {"wdg", "winding"}:
            active_winding = int(float(value)) - 1
            while len(windings) <= active_winding:
                windings.append({})
        elif active_winding is not None and key in {"bus", "conn", "kv", "kva", "%r"}:
            windings[active_winding][key] = value
    phase_count = _parse_int(properties.get("phases")) or inherited_phase_count or 3
    phase_labels = _default_phase_labels(phase_count)
    typed_windings = tuple(
        IEEE123TransformerWinding(
            winding=index + 1,
            bus=_parse_bus(str(winding.get("bus", "")), fallback_phase_count=phase_count),
            connection=None if winding.get("conn") in {None, ""} else str(winding.get("conn")),
            nominal_kv=float(winding["kv"]) if winding.get("kv") not in {None, ""} else None,
            rated_kva=float(winding["kva"]) if winding.get("kva") not in {None, ""} else None,
            resistance_percent=float(winding["%r"]) if winding.get("%r") not in {None, ""} else None,
        )
        for index, winding in enumerate(windings)
        if winding
    )
    return IEEE123Transformer(
        name=command.name,
        phases=phase_labels,
        windings=typed_windings,
        bank=properties.get("bank") or inherited_bank,
        xhl_percent=_parse_float(properties.get("xhl")) if properties.get("xhl") is not None else inherited_xhl,
        load_loss_percent=(
            _parse_float(properties.get("%loadloss"))
            if properties.get("%loadloss") is not None
            else inherited_load_loss
        ),
        like=like,
        source_record=_source_record(command),
    )


def _parse_regulator(
    command: _DSSCommand,
    prior_regulators: Mapping[str, IEEE123Regulator],
) -> IEEE123Regulator:
    items = _scan_assignment_items(command.text)
    properties = _items_to_last_map(items)
    like = properties.get("like")
    inherited = prior_regulators.get(like.lower()) if like is not None else None
    return IEEE123Regulator(
        name=command.name,
        transformer_name=properties.get("transformer") or (inherited.transformer_name if inherited is not None else ""),
        winding=_parse_int(properties.get("winding")) if properties.get("winding") is not None else (inherited.winding if inherited is not None else None),
        voltage_regulation=(
            _parse_float(properties.get("vreg"))
            if properties.get("vreg") is not None
            else (inherited.voltage_regulation if inherited is not None else None)
        ),
        band=_parse_float(properties.get("band")) if properties.get("band") is not None else (inherited.band if inherited is not None else None),
        potential_transformer_ratio=(
            _parse_float(properties.get("ptratio"))
            if properties.get("ptratio") is not None
            else (inherited.potential_transformer_ratio if inherited is not None else None)
        ),
        current_transformer_primary=(
            _parse_float(properties.get("ctprim"))
            if properties.get("ctprim") is not None
            else (inherited.current_transformer_primary if inherited is not None else None)
        ),
        resistance_setting=(
            _parse_float(properties.get("r"))
            if properties.get("r") is not None
            else (inherited.resistance_setting if inherited is not None else None)
        ),
        reactance_setting=(
            _parse_float(properties.get("x"))
            if properties.get("x") is not None
            else (inherited.reactance_setting if inherited is not None else None)
        ),
        like=like,
        source_record=_source_record(command),
    )


def _parse_load(command: _DSSCommand) -> IEEE123Load:
    items = _scan_assignment_items(command.text)
    properties = _items_to_last_map(items)
    declared_phase_count = _parse_int(properties.get("phases")) or 1
    bus = _parse_bus(properties.get("bus1", ""), fallback_phase_count=declared_phase_count)
    return IEEE123Load(
        name=command.name,
        bus=bus,
        declared_phase_count=declared_phase_count,
        connection=str(properties.get("conn", "")),
        model=_parse_int(properties.get("model")),
        nominal_kv=_parse_float(properties.get("kv")),
        active_power_kw=float(properties.get("kw", "0")),
        reactive_power_kvar=float(properties.get("kvar", "0")),
        source_record=_source_record(command),
    )


def _parse_capacitor(command: _DSSCommand) -> IEEE123Capacitor:
    items = _scan_assignment_items(command.text)
    properties = _items_to_last_map(items)
    phase_count = _parse_int(properties.get("phases")) or 3
    bus = _parse_bus(properties.get("bus1", ""), fallback_phase_count=phase_count)
    return IEEE123Capacitor(
        name=command.name,
        bus=bus,
        phase_count=phase_count,
        reactive_power_kvar=float(properties.get("kvar", "0")),
        nominal_kv=_parse_float(properties.get("kv")),
        source_record=_source_record(command),
    )


def _source_metadata(config: Mapping[str, Any], source_path: Path) -> dict[str, str]:
    digest = sha256_file(source_path)
    expected = str(config["source"].get("sha256", "")).removeprefix("sha256:")
    if expected and expected != digest:
        raise ValueError(f"checksum mismatch for {source_path}: expected {expected}, got {digest}")
    return {
        "source_sha256": digest,
        "source_version": str(config["source"].get("version", "")),
        "source_url": str(config["source"].get("url", "")),
        "source_license": str(config["source"].get("license", "")),
        "transformation": str(config["source"].get("transformation", "")),
    }


def _verify_auxiliary_digest(config: Mapping[str, Any], key: str, digest_key: str) -> str:
    path = Path(str(config["source"][key]))
    digest = sha256_file(path)
    expected = str(config["source"].get(digest_key, "")).removeprefix("sha256:")
    if expected and expected != digest:
        raise ValueError(f"checksum mismatch for {path}: expected {expected}, got {digest}")
    return digest


def _register_bus_reference(
    bus_index: dict[str, set[str]],
    source_records: dict[str, list[str]],
    connection: BusPhaseConnection,
    record: str,
) -> None:
    if not connection.bus_id:
        return
    bus_index.setdefault(connection.bus_id, set()).update(connection.phases)
    source_records.setdefault(connection.bus_id, []).append(record)


def _sorted_bus_ids(values: Iterable[str]) -> list[str]:
    def key(bus_id: str) -> tuple[int, str]:
        return (len(bus_id), bus_id)

    return sorted(set(values), key=key)


def _build_public_grid(
    *,
    config: Mapping[str, Any],
    source_path: Path,
    loads: Sequence[IEEE123Load],
    lines: Sequence[IEEE123Line],
    transformers: Sequence[IEEE123Transformer],
    bus_records: Mapping[str, list[str]],
    bus_index: Mapping[str, set[str]],
    parsed_files: Sequence[Path],
    auxiliary_hashes: Mapping[str, str],
) -> PublicGridDataWithMetadata:
    loads_kw: dict[str, float] = {}
    for load in loads:
        loads_kw[load.bus.bus_id] = loads_kw.get(load.bus.bus_id, 0.0) + load.active_power_kw
    node_ids = set(bus_index)
    for line in lines:
        node_ids.add(line.from_bus.bus_id)
        node_ids.add(line.to_bus.bus_id)
    for transformer in transformers:
        for winding in transformer.windings:
            node_ids.add(winding.bus.bus_id)
    nodes = tuple(
        PublicNode(
            node_id=bus_id,
            load_kw=loads_kw.get(bus_id, 0.0),
            generation_kw=0.0,
            source_record=" | ".join(bus_records.get(bus_id, [f"IEEE123 feeder bus={bus_id}"])),
        )
        for bus_id in _sorted_bus_ids(node_ids)
    )
    line_edges = [
        PublicEdge(
            edge_id=f"line_{line.name}",
            source=line.from_bus.bus_id,
            target=line.to_bus.bus_id,
            capacity_kw=None,
            in_service=line.in_service,
            source_record=line.source_record,
        )
        for line in lines
    ]
    transformer_edges = [
        PublicEdge(
            edge_id=f"transformer_{transformer.name}",
            source=transformer.windings[0].bus.bus_id,
            target=transformer.windings[1].bus.bus_id,
            capacity_kw=None,
            in_service=True,
            source_record=transformer.source_record,
        )
        for transformer in transformers
        if len(transformer.windings) >= 2
    ]
    contingencies: list[PublicContingency] = []
    for edge in line_edges:
        if edge.in_service:
            contingencies.append(
                PublicContingency(
                    contingency_id=f"deterministic_n_1_{edge.edge_id}",
                    component_kind="branch",
                    component_id=edge.edge_id,
                    action="open one listed in-service IEEE123 feeder line or switch",
                    source_record=edge.source_record,
                )
            )
    for edge in transformer_edges:
        contingencies.append(
            PublicContingency(
                contingency_id=f"deterministic_n_1_{edge.edge_id}",
                component_kind="transformer",
                component_id=edge.edge_id,
                action="open one listed in-service IEEE123 transformer",
                source_record=edge.source_record,
            )
        )
    metadata = {
        "parsed_files": tuple(str(path) for path in parsed_files),
        "auxiliary_source_sha256": dict(auxiliary_hashes),
        "published_line_ratings_available": False,
        "published_line_rating_note": (
            "The published IEEE 123-bus OpenDSS source lists no explicit NormalAmps/EmergAmps values; "
            "the adapter retains line normal_amps=None."
        ),
        "phase_connections_preserved": True,
        "switch_count": sum(1 for line in lines if line.is_switch),
        "open_switch_count": sum(1 for line in lines if line.is_switch and not line.in_service),
    }
    return PublicGridDataWithMetadata(
        benchmark=str(config["benchmark"]["id"]),
        family=str(config["benchmark"]["family"]),
        nodes=nodes,
        edges=tuple(line_edges + transformer_edges),
        contingencies=tuple(contingencies),
        source_path=str(source_path),
        metadata=metadata,
        **_source_metadata(config, source_path),
    )


def parse_ieee123_sc_cmpo_case(config: Mapping[str, Any]) -> IEEE123SCMPOCase:
    """Parse the configured IEEE 123-bus OpenDSS feeder into typed records."""

    source_path = Path(str(config["source"]["local_path"]))
    load_path = Path(str(config["source"]["load_path"]))
    regulator_path = Path(str(config["source"]["regulator_path"]))
    commands, parsed_files = _collect_commands(source_path)
    linecodes_by_name: dict[str, IEEE123LineCode] = {}
    transformers_by_name: dict[str, IEEE123Transformer] = {}
    regulators_by_name: dict[str, IEEE123Regulator] = {}
    linecodes: list[IEEE123LineCode] = []
    lines: list[IEEE123Line] = []
    loads: list[IEEE123Load] = []
    transformers: list[IEEE123Transformer] = []
    regulators: list[IEEE123Regulator] = []
    capacitors: list[IEEE123Capacitor] = []
    bus_index: dict[str, set[str]] = {}
    bus_records: dict[str, list[str]] = {}
    circuit_source_bus: BusPhaseConnection | None = None
    for command in commands:
        if command.kind == "circuit":
            circuit_props = _items_to_last_map(_scan_assignment_items(command.text))
            bus = _parse_bus(circuit_props.get("bus1", ""), fallback_phase_count=3)
            circuit_source_bus = bus
            _register_bus_reference(bus_index, bus_records, bus, _source_record(command))
            continue
        if command.kind == "linecode":
            linecode = _parse_linecode(command)
            linecodes.append(linecode)
            linecodes_by_name[linecode.code_id.lower()] = linecode
            continue
        if command.kind == "line":
            line = _parse_line(command, linecodes_by_name)
            lines.append(line)
            _register_bus_reference(bus_index, bus_records, line.from_bus, line.source_record)
            _register_bus_reference(bus_index, bus_records, line.to_bus, line.source_record)
            continue
        if command.kind == "load":
            load = _parse_load(command)
            loads.append(load)
            _register_bus_reference(bus_index, bus_records, load.bus, load.source_record)
            continue
        if command.kind == "transformer":
            transformer = _parse_transformer(command, transformers_by_name)
            transformers.append(transformer)
            transformers_by_name[transformer.name.lower()] = transformer
            for winding in transformer.windings:
                _register_bus_reference(bus_index, bus_records, winding.bus, transformer.source_record)
            continue
        if command.kind == "regcontrol":
            regulator = _parse_regulator(command, regulators_by_name)
            regulators.append(regulator)
            regulators_by_name[regulator.name.lower()] = regulator
            continue
        if command.kind == "capacitor":
            capacitor = _parse_capacitor(command)
            capacitors.append(capacitor)
            _register_bus_reference(bus_index, bus_records, capacitor.bus, capacitor.source_record)
    if circuit_source_bus is not None:
        _register_bus_reference(bus_index, bus_records, circuit_source_bus, "source circuit bus")
    buses = tuple(
        IEEE123Bus(
            bus_id=bus_id,
            phases=tuple(sorted(bus_index.get(bus_id, set()), key=int)) if bus_index.get(bus_id) else (),
            source_record=" | ".join(bus_records.get(bus_id, [f"IEEE123 feeder bus={bus_id}"])),
        )
        for bus_id in _sorted_bus_ids(bus_index)
    )
    auxiliary_hashes = {
        path_key: _verify_auxiliary_digest(config, path_key, digest_key)
        for path_key, digest_key in (
            ("load_path", "load_sha256"),
            ("regulator_path", "regulator_sha256"),
            ("switch_path", "switch_sha256"),
            ("linecode_path", "linecode_sha256"),
            ("license_path", "license_sha256"),
        )
    }
    grid = _build_public_grid(
        config=config,
        source_path=source_path,
        loads=loads,
        lines=lines,
        transformers=transformers,
        bus_records=bus_records,
        bus_index=bus_index,
        parsed_files=parsed_files,
        auxiliary_hashes=auxiliary_hashes,
    )
    metadata = {
        "master_path": str(source_path),
        "load_path": str(load_path),
        "regulator_path": str(regulator_path),
        "parsed_file_count": len(parsed_files),
        "published_line_ratings_available": False,
        "phase_connections_preserved": True,
        "total_active_power_kw": sum(load.active_power_kw for load in loads),
        "total_reactive_power_kvar": sum(load.reactive_power_kvar for load in loads),
    }
    return IEEE123SCMPOCase(
        benchmark=str(config["benchmark"]["id"]),
        buses=buses,
        lines=tuple(lines),
        loads=tuple(loads),
        transformers=tuple(transformers),
        regulators=tuple(regulators),
        capacitors=tuple(capacitors),
        line_codes=tuple(linecodes),
        grid=grid,
        metadata=metadata,
    )


def build_ieee123_microgrid_candidates(
    case: IEEE123SCMPOCase,
    *,
    count: int,
    patch_size: int,
    deterministic_seed: int,
) -> list[UpgradePatch]:
    """Select deterministic public-grid upgrade patches from the parsed feeder."""

    return select_upgrade_patches(
        case.grid,
        count=count,
        patch_size=patch_size,
        deterministic_seed=deterministic_seed,
    )


def validate_ieee123_powerflow(
    case: IEEE123SCMPOCase,
    *,
    minimum_voltage_floor_pu: float = 0.9,
    maximum_voltage_ceiling_pu: float = 1.1,
) -> dict[str, Any]:
    """Validate parser parity against OpenDSSDirect.py on the published feeder."""

    try:
        import opendssdirect as opendssdirect
        import dss as dss_python
    except ImportError as exc:  # pragma: no cover - exercised only on missing dependency
        raise RuntimeError("OpenDSSDirect.py validation requires opendssdirect and dss-python") from exc
    master_path = Path(case.metadata["master_path"]).resolve()
    original_working_directory = Path.cwd()
    try:
        opendssdirect.Basic.ClearAll()
        opendssdirect.Command(f"Compile [{master_path}]")
        compile_result = opendssdirect.Error.Description() if opendssdirect.Error.Number() else ""
    finally:
        os.chdir(original_working_directory)
    opendssdirect.Solution.Solve()
    solver_converged = bool(opendssdirect.Solution.Converged())
    solver_iterations = int(opendssdirect.Solution.Iterations())
    active_losses_w, reactive_losses_var = (float(value) for value in opendssdirect.Circuit.Losses())
    source_active_power_kw, source_reactive_power_kvar = (
        float(value) for value in opendssdirect.Circuit.TotalPower()
    )
    engine_counts = {
        "buses": len(opendssdirect.Circuit.AllBusNames()),
        "lines": int(opendssdirect.Lines.Count()),
        "loads": int(opendssdirect.Loads.Count()),
        "transformers": int(opendssdirect.Transformers.Count()),
        "regulators": int(opendssdirect.RegControls.Count()),
        "capacitors": int(opendssdirect.Capacitors.Count()),
    }
    engine_total_load_kw = 0.0
    engine_total_load_kvar = 0.0
    for name in opendssdirect.Loads.AllNames():
        opendssdirect.Loads.Name(name)
        engine_total_load_kw += float(opendssdirect.Loads.kW())
        engine_total_load_kvar += float(opendssdirect.Loads.kvar())
    bus_magnitudes = [value for value in opendssdirect.Circuit.AllBusMagPu() if value > 0.0]
    minimum_voltage_pu = min(bus_magnitudes)
    maximum_voltage_pu = max(bus_magnitudes)
    parser_bus_names = {bus.bus_id.lower() for bus in case.buses}
    parser_line_names = {line.name.lower() for line in case.lines}
    parser_load_names = {load.name.lower() for load in case.loads}
    parser_transformer_names = {transformer.name.lower() for transformer in case.transformers}
    parser_regulator_names = {regulator.name.lower() for regulator in case.regulators}
    parser_capacitor_names = {capacitor.name.lower() for capacitor in case.capacitors}
    checks = [
        {
            "name": "compile_succeeded",
            "passed": compile_result == "",
            "expected": "",
            "actual": compile_result,
        },
        {
            "name": "solver_converged",
            "passed": solver_converged,
            "expected": True,
            "actual": solver_converged,
        },
        {
            "name": "bus_count_matches",
            "passed": engine_counts["buses"] == len(case.grid.nodes),
            "expected": len(case.grid.nodes),
            "actual": engine_counts["buses"],
        },
        {
            "name": "line_count_matches",
            "passed": engine_counts["lines"] == len(case.lines),
            "expected": len(case.lines),
            "actual": engine_counts["lines"],
        },
        {
            "name": "load_count_matches",
            "passed": engine_counts["loads"] == len(case.loads),
            "expected": len(case.loads),
            "actual": engine_counts["loads"],
        },
        {
            "name": "transformer_count_matches",
            "passed": engine_counts["transformers"] == len(case.transformers),
            "expected": len(case.transformers),
            "actual": engine_counts["transformers"],
        },
        {
            "name": "regulator_count_matches",
            "passed": engine_counts["regulators"] == len(case.regulators),
            "expected": len(case.regulators),
            "actual": engine_counts["regulators"],
        },
        {
            "name": "capacitor_count_matches",
            "passed": engine_counts["capacitors"] == len(case.capacitors),
            "expected": len(case.capacitors),
            "actual": engine_counts["capacitors"],
        },
        {
            "name": "total_load_kw_matches",
            "passed": abs(engine_total_load_kw - sum(load.active_power_kw for load in case.loads)) <= 1e-9,
            "expected": sum(load.active_power_kw for load in case.loads),
            "actual": engine_total_load_kw,
        },
        {
            "name": "total_load_kvar_matches",
            "passed": abs(engine_total_load_kvar - sum(load.reactive_power_kvar for load in case.loads)) <= 1e-9,
            "expected": sum(load.reactive_power_kvar for load in case.loads),
            "actual": engine_total_load_kvar,
        },
        {
            "name": "bus_name_set_matches",
            "passed": parser_bus_names == {name.lower() for name in opendssdirect.Circuit.AllBusNames()},
            "expected": sorted(parser_bus_names),
            "actual": sorted(name.lower() for name in opendssdirect.Circuit.AllBusNames()),
        },
        {
            "name": "line_name_set_matches",
            "passed": parser_line_names == {name.lower() for name in opendssdirect.Lines.AllNames()},
            "expected": sorted(parser_line_names),
            "actual": sorted(name.lower() for name in opendssdirect.Lines.AllNames()),
        },
        {
            "name": "load_name_set_matches",
            "passed": parser_load_names == {name.lower() for name in opendssdirect.Loads.AllNames()},
            "expected": sorted(parser_load_names),
            "actual": sorted(name.lower() for name in opendssdirect.Loads.AllNames()),
        },
        {
            "name": "transformer_name_set_matches",
            "passed": parser_transformer_names == {name.lower() for name in opendssdirect.Transformers.AllNames()},
            "expected": sorted(parser_transformer_names),
            "actual": sorted(name.lower() for name in opendssdirect.Transformers.AllNames()),
        },
        {
            "name": "regulator_name_set_matches",
            "passed": parser_regulator_names == {name.lower() for name in opendssdirect.RegControls.AllNames()},
            "expected": sorted(parser_regulator_names),
            "actual": sorted(name.lower() for name in opendssdirect.RegControls.AllNames()),
        },
        {
            "name": "capacitor_name_set_matches",
            "passed": parser_capacitor_names == {name.lower() for name in opendssdirect.Capacitors.AllNames()},
            "expected": sorted(parser_capacitor_names),
            "actual": sorted(name.lower() for name in opendssdirect.Capacitors.AllNames()),
        },
        {
            "name": "minimum_voltage_within_bounds",
            "passed": minimum_voltage_pu >= minimum_voltage_floor_pu,
            "expected": minimum_voltage_floor_pu,
            "actual": minimum_voltage_pu,
        },
        {
            "name": "maximum_voltage_within_bounds",
            "passed": maximum_voltage_pu <= maximum_voltage_ceiling_pu,
            "expected": maximum_voltage_ceiling_pu,
            "actual": maximum_voltage_pu,
        },
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "passed": passed,
        "engine": "OpenDSSDirect.py",
        "engine_version": opendssdirect.Basic.Version(),
        "opendssdirect_version": getattr(opendssdirect, "__version__", None),
        "dss_python_version": getattr(dss_python, "__version__", None),
        "solver_converged": solver_converged,
        "solver_iterations": solver_iterations,
        "engine_counts": engine_counts,
        "engine_total_load_kw": engine_total_load_kw,
        "engine_total_load_kvar": engine_total_load_kvar,
        "source_active_power_kw": source_active_power_kw,
        "source_reactive_power_kvar": source_reactive_power_kvar,
        "active_losses_kw": active_losses_w / 1000.0,
        "reactive_losses_kvar": reactive_losses_var / 1000.0,
        "minimum_voltage_pu": minimum_voltage_pu,
        "maximum_voltage_pu": maximum_voltage_pu,
        "checks": checks,
    }


__all__ = [
    "BusPhaseConnection",
    "IEEE123Bus",
    "IEEE123Capacitor",
    "IEEE123Line",
    "IEEE123LineCode",
    "IEEE123Load",
    "IEEE123Regulator",
    "IEEE123SCMPOCase",
    "IEEE123Transformer",
    "IEEE123TransformerWinding",
    "PublicGridDataWithMetadata",
    "build_ieee123_microgrid_candidates",
    "parse_ieee123_sc_cmpo_case",
    "validate_ieee123_powerflow",
]
