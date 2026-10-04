# Process brief: invoice exception handling (as-is)

*Input to the Module 1 design exercise. Based on interviews with the AP team of a mid-size manufacturer.*

Around 4,000 supplier invoices arrive each month by email as PDF or text. About 70% match their purchase order and goods receipt and are paid without anyone looking at them. The other 30% are **exceptions**. Six AP analysts spend most of their week on them. Average handling time is 14 minutes per exception and the backlog at month end delays accruals.

## What an analyst does today
1. **Reads the invoice** and keys the invoice number, vendor, PO reference, lines, tax and total into a worksheet. European vendors use a decimal comma, which causes keying errors.
2. **Checks the arithmetic**: lines add up to the subtotal, subtotal plus tax equals the total.
3. **Looks up four things** in the ERP, in any order: the purchase order, the goods receipts, the vendor master record, and whether the same invoice number was already posted for that vendor.
4. **Compares**: unit price against the PO (2% tolerance), invoiced quantity against received quantity (no tolerance), bank account on the invoice against the vendor master, vendor status.
5. **Decides** using the AP policies:
   - nothing wrong and under 10,000: approve and post
   - nothing wrong, 10,000 to 50,000: AP Manager approves
   - nothing wrong, above 50,000: Financial Controller approves
   - price variance: send to the buyer
   - quantity mismatch: hold, ask Receiving
   - duplicate: reject, return to vendor
   - no PO: send to the cost centre owner
   - bank details changed or vendor inactive: hold, refer to the Vendor Master team
6. **Writes a short note** for whoever must act, quoting the policy section. A senior analyst reviews notes from juniors and sends about one in five back for a missing policy reference.
7. **Waits for the approver** (email, sometimes days), then posts or closes the item.

## Constraints from the Controller
- The automation may never approve an invoice that the approval matrix assigns to a person.
- Bank details are never changed on the strength of an invoice.
- Every decision must be explainable from stored evidence for seven years.
- If a system is down, the invoice waits for a person. It is not guessed.
