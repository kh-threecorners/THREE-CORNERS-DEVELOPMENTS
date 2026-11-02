from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSalesManager(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.leader_a = Users.create({'name': 'Leader A', 'login': 'tc_leader_a'})
        cls.leader_b = Users.create({'name': 'Leader B', 'login': 'tc_leader_b'})
        cls.rep_a = Users.create({'name': 'Rep A', 'login': 'tc_rep_a'})
        cls.rep_b = Users.create({'name': 'Rep B', 'login': 'tc_rep_b'})
        cls.rep_no_team = Users.create({'name': 'Rep No Team', 'login': 'tc_rep_none'})
        cls.rep_no_leader = Users.create({'name': 'Rep No Leader', 'login': 'tc_rep_nolead'})
        Team = cls.env['crm.team']
        Team.create({'name': 'A', 'user_id': cls.leader_a.id, 'member_ids': [(6, 0, cls.rep_a.ids)]})
        Team.create({'name': 'B', 'user_id': cls.leader_b.id, 'member_ids': [(6, 0, cls.rep_b.ids)]})
        Team.create({'name': 'None', 'user_id': False, 'member_ids': [(6, 0, cls.rep_no_leader.ids)]})

    def setUp(self):
        super().setUp()
        self.booking = self.env['property.sale'].new({})

    def _set_rep(self, user):
        self.booking.internal_sales_person_id = user.partner_id

    def test_follows_team_leader(self):
        self._set_rep(self.rep_a)
        self.assertEqual(self.booking.sales_manager, self.leader_a.partner_id)
        self._set_rep(self.rep_b)
        self.assertEqual(self.booking.sales_manager, self.leader_b.partner_id)

    def test_empty_without_team_or_leader(self):
        self._set_rep(self.rep_a)
        self._set_rep(self.rep_no_team)
        self.assertFalse(self.booking.sales_manager)
        self._set_rep(self.rep_no_leader)
        self.assertFalse(self.booking.sales_manager)

    def test_partner_without_user_stays_empty(self):
        self.booking.internal_sales_person_id = self.env['res.partner'].create({'name': 'Outside'})
        self.assertFalse(self.booking.sales_manager)

    def test_manual_value_is_kept_until_rep_changes(self):
        self._set_rep(self.rep_a)
        self.booking.sales_manager = self.leader_b.partner_id
        self.assertEqual(self.booking.sales_manager, self.leader_b.partner_id)
        self._set_rep(self.rep_b)
        self._set_rep(self.rep_a)
        self.assertEqual(self.booking.sales_manager, self.leader_a.partner_id)

    def test_unit_type_labels(self):
        labels = dict(self.env['property.property']._fields['property_type'].selection)
        self.assertEqual(labels['land'], 'admin')
        self.assertEqual(labels['industry'], 'Medical')
        self.assertNotIn('Land', labels.values())
        self.assertNotIn('Industry', labels.values())
