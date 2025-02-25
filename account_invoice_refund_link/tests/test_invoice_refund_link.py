# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2014,2023,2025 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged

from .. import post_init_hook


@tagged("post_install", "-at_install")
class TestInvoiceRefundLinkBase(TransactionCase):
    refund_method = "refund"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )
        if not cls.env.company.chart_template_id:
            # Load a CoA if there's none in current company
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
            coa.try_loading(company=cls.env.company, install_demo=False)
        cls.partner = cls.env["res.partner"].create({"name": "Test partner"})
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.invoice_lines = [
            (0, False, {"name": "Test section", "display_type": "line_section"}),
            (0, False, {"name": "Test #1", "quantity": 1.0, "price_unit": 100.0}),
            (0, False, {"name": "Test #2", "quantity": 2.0, "price_unit": 25.0}),
        ]
        cls.invoice = cls.env["account.move"].create(
            {
                "partner_id": cls.partner.id,
                "move_type": "out_invoice",
                "invoice_line_ids": cls.invoice_lines,
            }
        )
        cls.invoice.action_post()
        cls.refund_reason = "The refund reason"
        cls.env["account.move.reversal"].with_context(
            active_ids=cls.invoice.ids, active_model="account.move"
        ).create(
            {
                "refund_method": cls.refund_method,
                "reason": cls.refund_reason,
                "journal_id": cls.journal.id,
            }
        ).reverse_moves()

    def _test_refund_link(self):
        self.assertTrue(self.invoice.refund_invoice_ids)
        refund = self.invoice.refund_invoice_ids[0]
        ref = "Reversal of: {}, {}".format(self.invoice.name, self.refund_reason)
        self.assertEqual(refund.ref, ref)
        self.assertEqual(len(self.invoice.invoice_line_ids), len(self.invoice_lines))
        self.assertEqual(len(refund.invoice_line_ids), len(self.invoice_lines))
        # We're checking only the 2nd and 3rd lines because the first is a line section
        self.assertTrue(refund.invoice_line_ids[1].origin_line_id)
        self.assertEqual(
            self.invoice.invoice_line_ids[1], refund.invoice_line_ids[1].origin_line_id
        )
        self.assertTrue(refund.invoice_line_ids[2].origin_line_id)
        self.assertEqual(
            self.invoice.invoice_line_ids[2], refund.invoice_line_ids[2].origin_line_id
        )


class TestInvoiceRefundLink(TestInvoiceRefundLinkBase):
    @classmethod
    def setUpClass(cls):
        super(TestInvoiceRefundLink, cls).setUpClass()

    def test_post_init_hook(self):
        self.assertTrue(self.invoice.refund_invoice_ids)
        refund = self.invoice.refund_invoice_ids[0]
        refund.invoice_line_ids.write({"origin_line_id": False})
        self.assertFalse(refund.mapped("invoice_line_ids.origin_line_id"))
        post_init_hook(self.env.cr, None)
        self.refund_reason = "The refund reason"
        self._test_refund_link()

    def test_refund_link(self):
        self._test_refund_link()

    def test_invoice_copy(self):
        refund = self.invoice.refund_invoice_ids[0]
        self.invoice.copy()
        self.assertEqual(
            refund.invoice_line_ids.origin_line_id, self.invoice.invoice_line_ids
        )

    def test_refund_copy(self):
        refund = self.invoice.refund_invoice_ids[0]
        refund.copy()
        self.assertEqual(
            self.invoice.invoice_line_ids, refund.invoice_line_ids.origin_line_id
        )


class TestInvoiceRefundCancelLink(TestInvoiceRefundLinkBase):
    refund_method = "cancel"

    def test_refund_link(self):
        self._test_refund_link()


class TestInvoiceRefundModifyLink(TestInvoiceRefundLinkBase):
    refund_method = "modify"

    def test_refund_link(self):
        self._test_refund_link()
