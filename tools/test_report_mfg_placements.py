import unittest
from report_mfg_placements import report


def check(ap_id=1, table='map', sites=None, flag=10):
    return dict(ap_id=ap_id, name='test', region='Existing region',
                original_acquisition_flag=flag,
                source_identity={'item_lots': [{'table': table, 'row_id': 100}]},
                physical_sites=[] if sites is None else sites)


def site(map_id='m60_40_40_00', xyz=(0, 0, 0)):
    return dict(map_id=map_id, map_local_xyz=list(xyz))


def reference(**changes):
    row = dict(map='m60_40_40_00', x=0, y=0, z=0, itemLotId=100, lotSource='map')
    row.update(changes)
    return row


def run(checks, references):
    return report({'checks': checks, 'sources_sha256': {}}, references, {'profile': 'vanilla'})


class PlacementTests(unittest.TestCase):
    def test_cross_tile_agreement_height_disagreement_and_new_position(self):
        refs = [reference(map='m60_41_40_00', x=-256)]
        self.assertEqual(run([check(sites=[site()])], refs)['checks'][0]['status'], 'agreement')
        refs[0]['y'] = 10
        self.assertEqual(run([check(sites=[site()])], refs)['checks'][0]['status'], 'coordinate_disagreement')
        self.assertEqual(run([check()], refs)['checks'][0]['status'], 'newly_positioned')

    def test_dlc_separate_and_interior_partial_not_invented(self):
        self.assertEqual(run([check(sites=[site()])], [reference(map='m61_40_40_00')])['checks'][0]['status'], 'different_map')
        self.assertEqual(run([check(sites=[site('m10_00_00_00')])], [reference(map='m10_00_00')])['checks'][0]['status'], 'agreement_partial_map')

    def test_equal_partial_interior_is_not_full_map_certification(self):
        result = run([check(sites=[site('m10_00_00')])], [reference(map='m10_00_00')])
        self.assertEqual(result['checks'][0]['status'], 'agreement_partial_map')
        self.assertEqual(result['region_comparison'], 'not_inferred')

    def test_shared_flag_and_wrong_table_preserved(self):
        rows = [check(), check(ap_id=2)]
        result = run(rows, [reference()])
        self.assertEqual(result['check_status_counts'], {'ambiguous_identity': 2})
        result = run([check(table='enemy')], [reference()])
        self.assertEqual(result['identity_status_counts'], {'unmatched': 1})

    def test_display_flag_does_not_override_lot_and_unknown_source_is_explicit(self):
        self.assertEqual(run([check()], [reference(eventFlag=999)])['checks'][0]['status'], 'newly_positioned')
        row = reference(source='enemy')
        del row['lotSource']
        self.assertEqual(run([check()], [row])['identity_status_counts'], {'unknown_identity': 1})

    def test_multiple_sites_and_mixed_references_not_reduced_to_first(self):
        sites = [site(xyz=(100, 0, 0)), site()]
        result = run([check(sites=sites)], [reference(), reference(x=50)])
        self.assertEqual(result['checks'][0]['status'], 'mixed_reference_sites')
        self.assertEqual(result['spatial_comparison_counts'], {'agreement': 1, 'coordinate_disagreement': 1})

    def test_partial_disagreement_and_full_variants(self):
        result = run([check(sites=[site('m10_00_00_00')])], [reference(map='m10_00_00', x=100)])
        self.assertEqual(result['checks'][0]['status'], 'coordinate_disagreement_partial_map')
        result = run([check(sites=[site('m10_00_00_00')])], [reference(map='m10_00_00_10')])
        self.assertEqual(result['checks'][0]['status'], 'different_map')

    def test_all_agreeing_mixed_precision_not_a_discrepancy(self):
        refs = [reference(), reference(map='m10_00_00')]
        result = run([check(sites=[site(), site('m10_00_00_00')])], refs)
        self.assertEqual(result['checks'][0]['status'], 'agreement_partial_map')

    def test_invalid_input_fails(self):
        for row in [reference(x=float('nan')), reference(lotSource='enemy_guess'), reference(map='bad'), reference(itemLotId=True)]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                run([check()], [row])
        with self.assertRaises(ValueError):
            run([check()], [reference(reference_id=1), reference(reference_id=1)])


if __name__ == '__main__':
    unittest.main()
