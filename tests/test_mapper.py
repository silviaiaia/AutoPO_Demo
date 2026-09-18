from __future__ import annotations

import pytest

from autopo.core.mapper import (
    CustomerMapper,
    SkuEntry,
    SkuLookup,
    build_default_sku_lookup,
    enrich_rows,
)

ENTRY = SkuEntry(
    material="ATP-1042-A17",
    module_material="MOD-1042",
    customer_material="C460-3373",
)


@pytest.fixture()
def lookup() -> SkuLookup:
    return SkuLookup([("10001", ENTRY)])


class TestCustomerMapper:
    def test_alias_collapses_to_the_canonical_code(self):
        # 10901 is a ship-to alias of Customer-A; both must map to one account.
        assert CustomerMapper().canonical("10901") == "10001"

    def test_canonical_code_maps_to_itself(self):
        assert CustomerMapper().canonical("10001") == "10001"

    def test_codes_are_normalised_before_lookup(self):
        # ERP exports often hand back "10901.0" or a padded string.
        assert CustomerMapper().canonical(" 10901.0 ") == "10001"

    def test_unknown_code_passes_through_untouched(self):
        assert CustomerMapper().canonical("99999") == "99999"


class TestSkuLookup:
    def test_finds_an_entry_by_module_material(self, lookup: SkuLookup):
        assert lookup.lookup("10001", "MOD-1042") is ENTRY

    def test_finds_an_entry_by_customer_material(self, lookup: SkuLookup):
        assert lookup.lookup("10001", "C460-3373") is ENTRY

    @pytest.mark.parametrize("key", ["c460-3373", "C460 3373", "C4603373", " C460-3373 "])
    def test_keys_ignore_case_spaces_and_dashes(self, lookup: SkuLookup, key: str):
        # PDFs wrap, hyphenate and pad part numbers inconsistently.
        assert lookup.lookup("10001", key) is ENTRY

    def test_the_same_part_under_another_customer_is_not_a_match(self, lookup: SkuLookup):
        assert lookup.lookup("10002", "C460-3373") is None

    def test_missing_key_returns_none(self, lookup: SkuLookup):
        assert lookup.lookup("10001", "NOPE-0000") is None

    def test_each_entry_is_indexed_under_both_of_its_keys(self, lookup: SkuLookup):
        assert len(lookup) == 2

    def test_entries_without_keys_are_not_indexed(self):
        blank = SkuEntry(material="ATP-0000-X00", module_material="", customer_material="")
        assert len(SkuLookup([("10001", blank)])) == 0

    def test_default_lookup_covers_the_whole_sku_table(self):
        from autopo.config import SKU_TABLE

        assert len(build_default_sku_lookup()) == len(SKU_TABLE) * 2


class TestEnrichRows:
    def test_resolves_the_internal_material_number(self, lookup: SkuLookup):
        rows = [{"Sold-to Party": "10001", "Customer Material": "C460-3373"}]
        assert enrich_rows(rows, lookup, CustomerMapper()) == 1
        assert rows[0]["Material"] == "ATP-1042-A17"

    def test_matches_through_a_customer_alias(self, lookup: SkuLookup):
        # The PO carries the ship-to code, the SKU table is keyed by sold-to.
        rows = [{"Sold-to Party": "10901", "Customer Material": "C460-3373"}]
        assert enrich_rows(rows, lookup, CustomerMapper()) == 1
        assert rows[0]["Material"] == "ATP-1042-A17"

    def test_backfills_a_module_material_missing_from_the_po(self, lookup: SkuLookup):
        rows = [{"Sold-to Party": "10001", "Customer Material": "C460-3373"}]
        enrich_rows(rows, lookup, CustomerMapper())
        assert rows[0]["Module Material"] == "MOD-1042"

    def test_keeps_the_module_material_the_po_already_carried(self, lookup: SkuLookup):
        rows = [
            {
                "Sold-to Party": "10001",
                "Customer Material": "C460-3373",
                "Module Material": "MOD-1042",
            }
        ]
        enrich_rows(rows, lookup, CustomerMapper())
        assert rows[0]["Module Material"] == "MOD-1042"

    def test_an_unknown_part_is_left_for_a_human_to_resolve(self, lookup: SkuLookup):
        rows = [{"Sold-to Party": "10001", "Customer Material": "MYSTERY-1"}]
        assert enrich_rows(rows, lookup, CustomerMapper()) == 0
        assert "Material" not in rows[0]

    def test_counts_only_the_rows_that_matched(self, lookup: SkuLookup):
        rows = [
            {"Sold-to Party": "10001", "Customer Material": "C460-3373"},
            {"Sold-to Party": "10001", "Customer Material": "MYSTERY-1"},
            {"Sold-to Party": "10001", "Module Material": "MOD-1042"},
        ]
        assert enrich_rows(rows, lookup, CustomerMapper()) == 2

    def test_a_row_matches_at_most_once(self, lookup: SkuLookup):
        # Both key columns point at the same entry; that is one match, not two.
        rows = [
            {
                "Sold-to Party": "10001",
                "Module Material": "MOD-1042",
                "Customer Material": "C460-3373",
            }
        ]
        assert enrich_rows(rows, lookup, CustomerMapper()) == 1

    def test_empty_input(self, lookup: SkuLookup):
        assert enrich_rows([], lookup, CustomerMapper()) == 0
