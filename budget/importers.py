import csv
import hashlib
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import ExclusionRule, MerchantMapping, Transaction


def _normalize_description(value):
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", (value or "").lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _description_signature(value, words=4):
    normalized = _normalize_description(value)
    if not normalized:
        return ""
    return " ".join(normalized.split()[:words])


def _find_mapping(description, mappings=None):
    if mappings is None:
        mappings = list(MerchantMapping.objects.select_related("category").all())

    # Fast exact match first
    exact = next(
        (
            m
            for m in mappings
            if (m.raw_description or "").strip().lower() == (description or "").strip().lower()
        ),
        None,
    )
    if exact:
        return exact

    desc_norm = _normalize_description(description)
    desc_sig = _description_signature(description)
    best = None
    best_score = -1

    for mapping in mappings:
        map_norm = _normalize_description(mapping.raw_description)
        if not map_norm:
            continue

        score = -1
        map_sig = _description_signature(mapping.raw_description)

        if desc_norm == map_norm:
            score = 400 + len(map_norm)
        elif desc_sig and map_sig and desc_sig == map_sig and len(desc_sig) >= 8:
            score = 300 + len(map_sig)
        elif desc_norm.startswith(map_norm) and len(map_norm) >= 10:
            score = 220 + len(map_norm)
        elif map_norm.startswith(desc_norm) and len(desc_norm) >= 10:
            score = 180 + len(desc_norm)
        elif map_norm in desc_norm and len(map_norm) >= 14:
            score = 120 + len(map_norm)

        if score > best_score:
            best = mapping
            best_score = score

    return best


def _match_exclusion_rule(description, source, rules=None, amount=None):
    # Collapse multiple spaces so rules entered with single spaces match WF's multi-space format.
    desc = re.sub(r"\s+", " ", (description or "").lower()).strip()
    if rules is None:
        rules = ExclusionRule.objects.filter(is_active=True)
    for rule in rules:
        if rule.source and rule.source != source:
            continue
        rule_text = re.sub(r"\s+", " ", rule.description_contains.lower()).strip()
        if rule_text not in desc:
            continue
        # Amount direction filter
        if amount is not None and rule.amount_direction != "either":
            if rule.amount_direction == "negative" and amount >= 0:
                continue
            if rule.amount_direction == "positive" and amount < 0:
                continue
        return rule
    return None


def _parse_wf_date(value):
    raw = (value or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported DATE format: {raw}")


def _parse_amount(value):
    raw = (value or "").strip().replace("$", "").replace(",", "")
    if raw.startswith("(") and raw.endswith(")"):
        raw = f"-{raw[1:-1]}"
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid AMOUNT: {value}") from exc


def wf_import_csv(file_obj, source):
    """
    Parse Wells Fargo CSV. Apply existing MerchantMappings automatically.
    - Rows already imported are skipped (idempotent).
    - Rows whose hash collides with an existing transaction are staged as potential duplicates
      for user review instead of being silently dropped.
    Returns (imported_count, skipped_count, staged_count, unmatched_descriptions, skip_details).
    """
    reader = csv.DictReader(file_obj.read().decode("utf-8-sig").splitlines())
    imported, skipped, staged = 0, 0, 0
    unmatched = set()
    skip_details = []
    mappings = list(MerchantMapping.objects.select_related("category").all())
    exclusion_rules = list(ExclusionRule.objects.filter(is_active=True))

    for row in reader:
        date_raw = (row.get("DATE") or "").strip()
        description = (row.get("DESCRIPTION") or "").strip()
        amount_raw = (row.get("AMOUNT") or "").strip()
        if not date_raw or not description or not amount_raw:
            continue

        parsed_date = _parse_wf_date(date_raw)
        parsed_amount = _parse_amount(amount_raw)
        # Include source in the hash so checking/credit rows don't collide.
        raw_hash = hashlib.sha256(
            f"{source}|{parsed_date}|{description}|{parsed_amount}".encode()
        ).hexdigest()
        legacy_hash = hashlib.sha256(
            f"{parsed_date}|{description}|{parsed_amount}".encode()
        ).hexdigest()

        if Transaction.objects.filter(import_hash=raw_hash).exists():
            # Original already imported. Stage each additional occurrence as a potential duplicate
            # using an indexed hash so N identical rows all get staged separately.
            n = Transaction.objects.filter(duplicate_source_hash=raw_hash).count()
            dup_hash = hashlib.sha256(f"{raw_hash}:dup:{n}".encode()).hexdigest()
            if not Transaction.objects.filter(import_hash=dup_hash).exists():
                mapping = _find_mapping(description, mappings)
                Transaction.objects.create(
                    date=parsed_date,
                    raw_description=description,
                    friendly_name=mapping.friendly_name if mapping else "",
                    amount=parsed_amount,
                    category=mapping.category if mapping else None,
                    source=source,
                    check_number=(row.get("CHECK #") or "").strip(),
                    status=(row.get("STATUS") or "").strip(),
                    import_hash=dup_hash,
                    is_excluded=True,
                    exclusion_note="Potential duplicate — awaiting review",
                    is_pending_duplicate=True,
                    duplicate_source_hash=raw_hash,
                )
                staged += 1
            else:
                skip_details.append(
                    {
                        "date": str(parsed_date),
                        "description": description,
                        "amount": str(parsed_amount),
                        "reason": "Already staged at this index",
                    }
                )
                skipped += 1
            continue

        legacy_tx = Transaction.objects.filter(import_hash=legacy_hash).first()
        if legacy_tx:
            # Upgrade legacy pre-source hash rows to source-aware hash and correct source label.
            legacy_tx.source = source
            legacy_tx.import_hash = raw_hash
            legacy_tx.check_number = (row.get("CHECK #") or "").strip()
            legacy_tx.status = (row.get("STATUS") or "").strip()
            legacy_tx.save(update_fields=["source", "import_hash", "check_number", "status"])
            skip_details.append(
                {
                    "date": str(parsed_date),
                    "description": description,
                    "amount": str(parsed_amount),
                    "reason": "Legacy hash upgraded (previously imported without source)",
                }
            )
            skipped += 1
            continue

        mapping = _find_mapping(description, mappings)
        exclusion_rule = _match_exclusion_rule(
            description, source, exclusion_rules, amount=parsed_amount
        )
        Transaction.objects.create(
            date=parsed_date,
            raw_description=description,
            friendly_name=mapping.friendly_name if mapping else "",
            amount=parsed_amount,
            category=mapping.category if mapping else None,
            source=source,
            check_number=(row.get("CHECK #") or "").strip(),
            status=(row.get("STATUS") or "").strip(),
            import_hash=raw_hash,
            is_excluded=bool(exclusion_rule),
            exclusion_note=(exclusion_rule.note if exclusion_rule else ""),
        )
        if not mapping and not exclusion_rule:
            unmatched.add(description)
        imported += 1

    return imported, skipped, staged, sorted(unmatched), skip_details


# Registry mapping bank key → importer function.
# Add new institutions here as they are supported.
BANK_IMPORTERS = {
    "wells_fargo": wf_import_csv,
}


def import_bank_csv(file_obj, source, bank):
    """
    Dispatch CSV import to the appropriate bank-specific parser.
    Returns (imported, skipped, staged, unmatched_descriptions, skip_details).
    """
    importer = BANK_IMPORTERS.get(bank)
    if importer is None:
        raise ValueError(f"Unsupported bank: {bank}")
    return importer(file_obj, source)
