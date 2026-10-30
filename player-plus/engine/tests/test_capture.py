"""capture.py: a photo's rows become proposals, matched to held cards; only the chosen become acts."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import capture as K  # noqa: E402

HELD = [{'id': 'c-hall', 'title': 'Book the hall'}, {'id': 'c-q', 'title': 'The autumn gathering'}]
ROWS = [{'title': 'Bake the bread', 'holder': 'person:member', 'minutes': 90, 'before': ['book the hall.'],
         'within': 'The Autumn Gathering'},
        {'title': 'Set out  the chairs', 'before': ['Bake the bread', 'Borrow a van']},
        {'title': 'Book the hall', 'within': 'The autumn gathering'},
        {'title': 'Bake the bread'},                       # the same sticky read twice
        {'title': '   '}]


class Capture(unittest.TestCase):
    def setUp(self):
        self.r = K.propose(ROWS, HELD, 'sha256:abc')
        self.p = {p['title']: p for p in self.r['proposals']}

    def test_every_row_is_a_proposal_never_a_line(self):
        self.assertEqual(len(self.r['proposals']), 3)
        self.assertTrue(all(p['reason'] == 'untrusted' for p in self.r['proposals']))

    def test_matching_by_words(self):
        self.assertEqual(self.p['Book the hall']['kind'], 'existing')
        self.assertEqual(self.p['Book the hall']['matches'], 'c-hall')
        self.assertEqual(self.p['Bake the bread']['before'], ['c-hall'])
        self.assertEqual(self.p['Bake the bread']['within'], 'c-q')

    def test_a_name_held_nowhere_is_an_open_end(self):
        chairs = self.p['Set out the chairs']
        self.assertEqual(chairs['open_ends'], ['Borrow a van'])
        self.assertEqual(self.r['unmatched'], [{'proposal': chairs['id'], 'names': 'Borrow a van'}])

    def test_only_the_chosen_become_acts_in_order(self):
        bread, chairs, hall = self.p['Bake the bread'], self.p['Set out the chairs'], self.p['Book the hall']
        acts = K.confirm(self.r['proposals'], [chairs['id'], bread['id']])
        self.assertEqual([a['proposal'] for a in acts], [bread['id'], chairs['id']])   # the predecessor first
        self.assertEqual(acts[0]['type'], 'card')
        self.assertEqual(acts[0]['body'], {'title': 'Bake the bread', 'holder': 'person:member', 'minutes': 90})
        self.assertEqual(acts[1]['links']['predecessor'], ['@' + bread['id']])
        none = K.confirm(self.r['proposals'], [])
        self.assertEqual(none, [])
        held = K.confirm(self.r['proposals'], [hall['id']])
        self.assertEqual((held[0]['type'], held[0]['for_holder_of'], held[0]['links']), (None, 'c-hall', {'within': ['c-q']}))

    def test_deterministic(self):
        self.assertEqual(K.dumps(K.propose(ROWS, HELD, 'sha256:abc')), K.dumps(self.r))


if __name__ == '__main__':
    unittest.main()
