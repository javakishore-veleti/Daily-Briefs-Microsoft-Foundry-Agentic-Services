import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from middleware.adapters.azure.ms_foundry.hr_assistant_agent.memory_store import HrMemoryStore
from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory as FoundryObjectsFactory
from middleware.adapters.daos.objects_factory import ObjectsFactory as DaoObjectsFactory
from middleware.common.dtos.app_config import AppConfig
from middleware.common.dtos.hr_assistant_dtos import (
    HrFoundryMemoryClearResponse,
    HrSampleDatasetBulkPopulateResponse,
    HrSampleDatasetJoineeStatus,
    HrSampleDatasetPopulateResponse,
    HrSampleDatasetStatusResponse,
)
from middleware.common.entity.joiner import JoinerInfo, JoinerPreferences
from middleware.common.utils.logger_util import get_logger, log_methods

_STATE_FILE = "_population_state.json"
_BULK_CONFIG_FILE = "_bulk_generator.json"
_JOINee_FILE = "joinee.json"
_DEFAULT_BULK_COUNT = 1000
_DEFAULT_SPAN_DAYS = 30


@log_methods
class HrSampleDatasetService:
    def __init__(self) -> None:
        self.name = "HrSampleDatasetService"
        self.description = "Loads New-Joinees JSON datasets into MongoDB and Foundry Memory"
        self.root = _datasets_root()

    def status(self) -> HrSampleDatasetStatusResponse:
        files = self._list_dataset_files()
        state = self._read_state()
        joinees: list[HrSampleDatasetJoineeStatus] = []
        dao = DaoObjectsFactory.get_instance()
        info_mgr = dao.get_joiner_info_mgr()
        for folder, path in files:
            payload = self._load_json(path)
            email = str(payload.get("email", "")).strip().lower()
            existing = info_mgr.find_by_email(email) if email else None
            entry = state.get("joinees", {}).get(folder, {})
            joinees.append(
                HrSampleDatasetJoineeStatus(
                    folder=folder,
                    display_name=_display_name(payload),
                    email=email,
                    joiner_info_id=existing.id if existing is not None else str(entry.get("joiner_info_id", "")),
                    mongo_populated=existing is not None,
                    memory_populated=bool(entry.get("memory_populated", False)),
                    joining_date=_joining_date(payload),
                )
            )
        mongo_ok = bool(joinees) and all(item.mongo_populated for item in joinees)
        memory_ok = bool(joinees) and all(item.memory_populated for item in joinees)
        bulk_cfg = self._bulk_config()
        target = int(bulk_cfg.get("count", _DEFAULT_BULK_COUNT) or _DEFAULT_BULK_COUNT)
        span_days = int(bulk_cfg.get("span_days", _DEFAULT_SPAN_DAYS) or _DEFAULT_SPAN_DAYS)
        prefix = str(bulk_cfg.get("email_prefix", "joinee.bulk")).strip() or "joinee.bulk"
        domain = str(bulk_cfg.get("email_domain", "example.com")).strip() or "example.com"
        bulk_mongo_count = info_mgr.count_by_email_prefix(f"{prefix}.", domain)
        bulk_state = state.get("bulk", {})
        if not isinstance(bulk_state, dict):
            bulk_state = {}
        return HrSampleDatasetStatusResponse(
            dataset_path=str(self.root.relative_to(_repo_root())),
            joinee_count=len(joinees),
            populated=mongo_ok and memory_ok,
            mongo_populated=mongo_ok,
            memory_populated=memory_ok,
            populated_at=str(state.get("populated_at", "")),
            joinees=joinees,
            bulk_target_count=target,
            bulk_span_days=span_days,
            bulk_mongo_count=bulk_mongo_count,
            bulk_populated=bulk_mongo_count >= target,
            bulk_memory_seeded=bool(bulk_state.get("memory_seeded", False)),
            bulk_populated_at=str(bulk_state.get("populated_at", "")),
        )

    def populate(self, seed_memory: bool = True) -> HrSampleDatasetPopulateResponse:
        files = self._list_dataset_files()
        if not files:
            return HrSampleDatasetPopulateResponse(
                message=f"No {_JOINee_FILE} files found under {self.root}",
                status=self.status(),
            )
        dao = DaoObjectsFactory.get_instance()
        info_mgr = dao.get_joiner_info_mgr()
        pref_mgr = dao.get_joiner_preferences_mgr()
        memory = HrMemoryStore()
        project_client = None
        if seed_memory:
            project_client = FoundryObjectsFactory.get_instance().get_ms_foundry_project_client()
            memory.ensure(project_client)

        state = self._read_state()
        joinee_state: dict[str, Any] = dict(state.get("joinees", {}))
        created = 0
        skipped = 0
        memory_seeded = 0
        for folder, path in files:
            payload = self._load_json(path)
            email = str(payload.get("email", "")).strip().lower()
            if not email:
                get_logger(__name__).warning("dataset folder=%s missing email", folder)
                continue
            existing = info_mgr.find_by_email(email)
            if existing is None:
                joiner = self._to_joiner(payload)
                info_mgr.store(joiner)
                preference = self._to_preferences(joiner.id, payload)
                pref_mgr.store(preference)
                created += 1
                joiner_id = joiner.id
                prefs = preference
            else:
                skipped += 1
                joiner_id = existing.id
                prefs = pref_mgr.for_joiner(joiner_id)
                if prefs is None:
                    prefs = self._to_preferences(joiner_id, payload)
                    pref_mgr.store(prefs)

            memory_ok = bool(joinee_state.get(folder, {}).get("memory_populated", False))
            if seed_memory and project_client is not None and prefs is not None:
                text = _preference_memory_text(payload, prefs)
                memory.remember(project_client, joiner_id, text, wait=False)
                memory_ok = True
                memory_seeded += 1
            joinee_state[folder] = {
                "email": email,
                "joiner_info_id": joiner_id,
                "mongo_populated": True,
                "memory_populated": memory_ok,
            }

        populated_at = datetime.now(timezone.utc).isoformat()
        next_state = dict(state)
        next_state["populated_at"] = populated_at
        next_state["joinees"] = joinee_state
        self._write_state(next_state)
        status = self.status()
        message = (
            f"Loaded {created} hand-authored joinee(s) into MongoDB"
            + (f", skipped {skipped} already present" if skipped else "")
            + (f"; seeded Foundry Memory for {memory_seeded} joinee(s) in the background" if memory_seeded else "")
            + "."
        )
        return HrSampleDatasetPopulateResponse(
            message=message,
            status=status,
            created=created,
            skipped=skipped,
            memory_seeded=memory_seeded,
        )

    def clear_foundry_memory(self) -> HrFoundryMemoryClearResponse:
        """Wipe all HR Foundry memories by deleting and recreating the store."""
        store_name = AppConfig.get_instance().get_hr_memory_store_name()
        memory = HrMemoryStore()
        project_client = FoundryObjectsFactory.get_instance().get_ms_foundry_project_client()
        memory.clear_all(project_client)

        state = self._read_state()
        joinee_state = state.get("joinees", {})
        if isinstance(joinee_state, dict):
            for entry in joinee_state.values():
                if isinstance(entry, dict):
                    entry["memory_populated"] = False
            state["joinees"] = joinee_state
        bulk_state = state.get("bulk", {})
        if not isinstance(bulk_state, dict):
            bulk_state = {}
        bulk_state["memory_seeded"] = False
        bulk_state["memory_cleared_at"] = datetime.now(timezone.utc).isoformat()
        state["bulk"] = bulk_state
        self._write_state(state)

        status = self.status()
        return HrFoundryMemoryClearResponse(
            message=(
                f"Cleared Azure Foundry memory store '{store_name}' "
                "(deleted and recreated). Mongo joiner data was left unchanged."
            ),
            status=status,
            memory_store_name=store_name,
            cleared=True,
        )

    def populate_bulk(self, seed_memory: bool = False) -> HrSampleDatasetBulkPopulateResponse:
        cfg = self._bulk_config()
        target = max(1, min(int(cfg.get("count", _DEFAULT_BULK_COUNT) or _DEFAULT_BULK_COUNT), 5000))
        span_days = max(1, min(int(cfg.get("span_days", _DEFAULT_SPAN_DAYS) or _DEFAULT_SPAN_DAYS), 366))
        prefix = str(cfg.get("email_prefix", "joinee.bulk")).strip() or "joinee.bulk"
        domain = str(cfg.get("email_domain", "example.com")).strip() or "example.com"

        dao = DaoObjectsFactory.get_instance()
        info_mgr = dao.get_joiner_info_mgr()
        pref_mgr = dao.get_joiner_preferences_mgr()
        memory = HrMemoryStore()
        project_client = None
        if seed_memory:
            project_client = FoundryObjectsFactory.get_instance().get_ms_foundry_project_client()
            memory.ensure(project_client)

        created = 0
        skipped = 0
        memory_seeded = 0
        for index in range(1, target + 1):
            payload = _generate_bulk_payload(cfg, index, span_days, prefix, domain)
            email = str(payload["email"])
            existing = info_mgr.find_by_email(email)
            if existing is None:
                joiner = self._to_joiner(payload)
                info_mgr.store(joiner)
                preference = self._to_preferences(joiner.id, payload)
                pref_mgr.store(preference)
                created += 1
                joiner_id = joiner.id
                prefs = preference
            else:
                skipped += 1
                joiner_id = existing.id
                prefs = pref_mgr.for_joiner(joiner_id)
                if prefs is None:
                    prefs = self._to_preferences(joiner_id, payload)
                    pref_mgr.store(prefs)

            if seed_memory and project_client is not None and prefs is not None:
                memory.remember(
                    project_client,
                    joiner_id,
                    _preference_memory_text(payload, prefs),
                    wait=False,
                )
                memory_seeded += 1

            if index % 100 == 0:
                get_logger(__name__).info("bulk populate progress %s/%s created=%s skipped=%s", index, target, created, skipped)

        populated_at = datetime.now(timezone.utc).isoformat()
        state = self._read_state()
        state["bulk"] = {
            "populated_at": populated_at,
            "target_count": target,
            "span_days": span_days,
            "created": created,
            "skipped": skipped,
            "memory_seeded": seed_memory and memory_seeded > 0,
            "memory_seeded_count": memory_seeded,
        }
        self._write_state(state)
        status = self.status()
        message = (
            f"Bulk loaded {created} joinee(s) into MongoDB across {span_days} day(s)"
            + (f", skipped {skipped} already present" if skipped else "")
            + (
                f"; queued Foundry Memory updates for {memory_seeded} joinee(s) (background)"
                if memory_seeded
                else "; Foundry Memory not seeded (enable seed_memory to queue profile updates)"
            )
            + "."
        )
        return HrSampleDatasetBulkPopulateResponse(
            message=message,
            status=status,
            created=created,
            skipped=skipped,
            memory_seeded=memory_seeded,
            target_count=target,
            span_days=span_days,
            seed_memory=seed_memory,
        )

    def _bulk_config(self) -> dict[str, Any]:
        path = self.root / _BULK_CONFIG_FILE
        if not path.is_file():
            return {"count": _DEFAULT_BULK_COUNT, "span_days": _DEFAULT_SPAN_DAYS}
        try:
            payload = self._load_json(path)
            return payload
        except (OSError, ValueError, json.JSONDecodeError):
            get_logger(__name__).exception("failed to read %s", path)
            return {"count": _DEFAULT_BULK_COUNT, "span_days": _DEFAULT_SPAN_DAYS}

    def _list_dataset_files(self) -> list[tuple[str, Path]]:
        if not self.root.is_dir():
            return []
        rows: list[tuple[str, Path]] = []
        for child in sorted(self.root.iterdir()):
            if not child.is_dir() or child.name.startswith("_"):
                continue
            path = child / _JOINee_FILE
            if path.is_file():
                rows.append((child.name, path))
        return rows

    def _load_json(self, path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"{path} must contain a JSON object")
        return payload

    def _read_state(self) -> dict[str, Any]:
        path = self.root / _STATE_FILE
        if not path.is_file():
            return {}
        try:
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            get_logger(__name__).exception("failed to read %s", path)
            return {}

    def _write_state(self, payload: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / _STATE_FILE
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    def _to_joiner(self, payload: dict[str, Any]) -> JoinerInfo:
        joiner = JoinerInfo()
        joiner.first_name = str(payload.get("first_name", ""))
        joiner.middle_name = str(payload.get("middle_name", ""))
        joiner.last_name = str(payload.get("last_name", ""))
        joiner.email = str(payload.get("email", "")).strip().lower()
        joiner.contact_phone = str(payload.get("contact_phone", ""))
        joiner.contact_address = str(payload.get("contact_address", ""))
        joiner.interviewed_by_employee_ids = [str(item) for item in payload.get("interviewed_by_employee_ids", [])]
        joiner.interviewed_by_employee_names = [str(item) for item in payload.get("interviewed_by_employee_names", [])]
        joiner.official_role_name = str(payload.get("official_role_name", ""))
        joiner.internal_role_name = str(payload.get("internal_role_name", ""))
        joiner.joining_official_role_name = str(payload.get("joining_official_role_name", ""))
        joiner.salary_accepted_usd = float(payload.get("salary_accepted_usd", 0) or 0)
        joiner.joining_date = _joining_date(payload)
        return joiner

    def _to_preferences(self, joiner_info_id: str, payload: dict[str, Any]) -> JoinerPreferences:
        prefs_payload = payload.get("preferences")
        if not isinstance(prefs_payload, dict):
            prefs_payload = {}
        preference = JoinerPreferences()
        preference.joiner_info_id = joiner_info_id
        preference.resumes = str(prefs_payload.get("resumes", ""))
        preference.personal_interests = str(prefs_payload.get("personal_interests", ""))
        preference.food_preferences = str(prefs_payload.get("food_preferences", ""))
        return preference


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _datasets_root() -> Path:
    return _repo_root() / "DataSets" / "HR-Brief" / "New-Joinees"


def _display_name(payload: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in (
            str(payload.get("first_name", "")).strip(),
            str(payload.get("middle_name", "")).strip(),
            str(payload.get("last_name", "")).strip(),
        )
        if part
    )


def _joining_date(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("joining_date", "")).strip()
    if explicit:
        return explicit
    offset = int(payload.get("joining_date_offset_days", 0) or 0)
    return (date.today() + timedelta(days=offset)).isoformat()


def _preference_memory_text(payload: dict[str, Any], preferences: JoinerPreferences) -> str:
    name = _display_name(payload)
    return (
        f"Remember this profile for {name}. "
        f"Food preferences: {preferences.food_preferences}. "
        f"Personal interests: {preferences.personal_interests}. "
        f"Resumes: {preferences.resumes}."
    )


def _generate_bulk_payload(
    cfg: dict[str, Any],
    index: int,
    span_days: int,
    prefix: str,
    domain: str,
) -> dict[str, Any]:
    first_names = [str(item) for item in cfg.get("first_names", [])] or ["Joinee"]
    last_names = [str(item) for item in cfg.get("last_names", [])] or ["Sample"]
    cities = cfg.get("cities", []) or [["Global City", "World"]]
    streets = [str(item) for item in cfg.get("street_patterns", [])] or ["{n} Market Street"]
    roles = _weighted_roles(cfg.get("roles", []))
    interviewers = cfg.get("interviewers", []) or [["e-100", "Hiring Manager"]]
    interests = [str(item) for item in cfg.get("interests", [])] or ["Reading and hiking."]
    foods = [str(item) for item in cfg.get("food_preferences", [])] or ["No peanuts."]
    prior_roles = [str(item) for item in cfg.get("prior_roles", [])] or ["Software Engineer"]
    domains = [str(item) for item in cfg.get("domains", [])] or ["cloud platforms"]
    companies = [str(item) for item in cfg.get("companies", [])] or ["Contoso Systems"]
    experience_templates = cfg.get("past_experience_by_band", {})
    if not isinstance(experience_templates, dict):
        experience_templates = {}

    first = first_names[(index * 11 - 1) % len(first_names)]
    last = last_names[(index * 17 - 1) % len(last_names)]
    middle = "" if index % 4 else first_names[(index * 3) % len(first_names)][:1]
    city_row = cities[(index * 13 - 1) % len(cities)]
    city = str(city_row[0]) if isinstance(city_row, (list, tuple)) and city_row else "Global City"
    country = str(city_row[1]) if isinstance(city_row, (list, tuple)) and len(city_row) > 1 else "World"
    street = streets[(index * 5 - 1) % len(streets)].format(n=10 + (index * 9) % 190)
    role = roles[(index * 19 - 1) % len(roles)]
    official = str(role.get("official_role_name", "Software Engineer"))
    internal = str(role.get("internal_role_name", "IC3"))
    joining = str(role.get("joining_official_role_name", official))
    salary = _salary_for(role, index)
    band = str(role.get("experience_band", "mid"))
    templates = [str(item) for item in experience_templates.get(band, [])] or [
        "Prior experience in {domain} at {company}."
    ]
    experience = templates[(index * 23 - 1) % len(templates)].format(
        domain=domains[(index * 29 - 1) % len(domains)],
        company=companies[(index * 31 - 1) % len(companies)],
        prior_role=prior_roles[(index * 37 - 1) % len(prior_roles)],
        years=1 + (index % 18),
        months=2 + (index % 10),
        team_size=8 + (index % 120),
    )
    interviewer_count = 1 + (index % 3)
    selected_interviewers = [
        interviewers[(index + offset - 1) % len(interviewers)] for offset in range(interviewer_count)
    ]
    interviewer_ids = [
        str(item[0]) if isinstance(item, (list, tuple)) else "e-100" for item in selected_interviewers
    ]
    interviewer_names = [
        str(item[1]) if isinstance(item, (list, tuple)) and len(item) > 1 else "Hiring Manager"
        for item in selected_interviewers
    ]
    offset = (index * 7 - 1) % span_days
    email = f"{prefix}.{index:04d}@{domain}".lower()
    interest = interests[(index * 41 - 1) % len(interests)]
    food = foods[(index * 43 - 1) % len(foods)]
    persona_bits = _persona_bits(cfg, index)
    resume = (
        f"{first} {last} — joining as {joining}. Past experience: {experience} "
        f"{persona_bits['resume_extra']}"
    ).strip()
    interest_line = f"{interest} {persona_bits['interest_extra']}".strip()
    return {
        "first_name": first,
        "middle_name": middle,
        "last_name": last,
        "email": email,
        "contact_phone": f"+{1 + (index % 98)}-{200 + (index % 700):03d}-{1000 + (index % 9000):04d}",
        "contact_address": f"{street}, {city}, {country}",
        "interviewed_by_employee_ids": interviewer_ids,
        "interviewed_by_employee_names": interviewer_names,
        "official_role_name": official,
        "internal_role_name": internal,
        "joining_official_role_name": joining,
        "salary_accepted_usd": salary,
        "joining_date_offset_days": offset,
        "preferences": {
            "resumes": resume,
            "personal_interests": interest_line,
            "food_preferences": food,
        },
    }


def _persona_bits(cfg: dict[str, Any], index: int) -> dict[str, str]:
    personas = cfg.get("personas", [])
    certifications = [str(item) for item in cfg.get("certifications", [])]
    degrees = [str(item) for item in cfg.get("degrees", [])]
    resume_parts: list[str] = []
    interest_parts: list[str] = []
    if isinstance(personas, list) and personas:
        persona = personas[(index * 47 - 1) % len(personas)]
        if isinstance(persona, dict):
            key = str(persona.get("key", ""))
            blurb = str(persona.get("blurb", "")).strip()
            label = str(persona.get("label", key)).strip()
            if blurb:
                resume_parts.append(blurb)
            if label:
                interest_parts.append(f"Persona: {label}.")
            if key in {"certified", "scholar", "advanced_degree"} and certifications:
                cert = certifications[(index * 53 - 1) % len(certifications)]
                resume_parts.append(f"Certification: {cert}.")
            if key in {"scholar", "advanced_degree"} and degrees:
                degree = degrees[(index * 59 - 1) % len(degrees)]
                resume_parts.append(f"Highest degree: {degree}.")
            if key in {"author", "writer"}:
                resume_parts.append("Published writing portfolio includes books/articles.")
            if key == "athlete":
                resume_parts.append("Maintains competitive athletic training schedule.")
            if key == "artist":
                resume_parts.append("Active arts practice alongside professional career.")
    elif certifications:
        resume_parts.append(f"Certification: {certifications[(index - 1) % len(certifications)]}.")
    return {
        "resume_extra": " ".join(resume_parts),
        "interest_extra": " ".join(interest_parts),
    }


def _weighted_roles(raw_roles: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(raw_roles, list) or not raw_roles:
        return [
            {
                "official_role_name": "Software Engineer",
                "internal_role_name": "IC3",
                "joining_official_role_name": "Software Engineer",
                "salary_min": 90000,
                "salary_max": 120000,
                "experience_band": "mid",
            }
        ]
    for item in raw_roles:
        if isinstance(item, dict):
            weight = max(1, int(item.get("weight", 1) or 1))
            rows.extend([item] * weight)
            continue
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            rows.append(
                {
                    "official_role_name": str(item[0]),
                    "internal_role_name": str(item[1]),
                    "joining_official_role_name": str(item[0]),
                    "salary_min": float(item[2]),
                    "salary_max": float(item[2]),
                    "experience_band": "mid",
                }
            )
    return rows or [
        {
            "official_role_name": "Software Engineer",
            "internal_role_name": "IC3",
            "joining_official_role_name": "Software Engineer",
            "salary_min": 90000,
            "salary_max": 120000,
            "experience_band": "mid",
        }
    ]


def _salary_for(role: dict[str, Any], index: int) -> float:
    low = float(role.get("salary_min", role.get("salary_accepted_usd", 90000)) or 90000)
    high = float(role.get("salary_max", low) or low)
    if high < low:
        high = low
    span = max(0.0, high - low)
    return round(low + (span * ((index * 17) % 100) / 100.0), 2)
